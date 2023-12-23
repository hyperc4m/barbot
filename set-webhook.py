#!/usr/bin/env python3
import json
import os
import urllib.request
import subprocess

os.chdir(os.path.normpath(os.path.join(__file__, '..')))

p = subprocess.run(['terraform', 'output', '-json'], cwd='./terraform', stdout=subprocess.PIPE, text=True)
outputs = json.loads(p.stdout)

bot_token = outputs['telegram_bot_token']['value']
webhook_url = outputs['webhook_url']['value']
webhook_secret = outputs['webhook_secret']['value']

request = urllib.request.Request(
    url=f'https://api.telegram.org/bot{bot_token}/setWebhook',
    data=json.dumps({
        'url': webhook_url,
        'secret_token': webhook_secret
    }).encode('utf-8'),
    headers={
        'Content-Type': 'application/json',
        'User-Agent': 'barbot by @ceresgalax'
    },
    method='POST'
)

with urllib.request.urlopen(request) as response:
    if response.status < 200 or response.status >= 300:
        print('Failed to set webhook')
        exit(1)

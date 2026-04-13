lines = open(r'D:\RR_Repo\tools\ingest_asset.py', encoding='utf-8').readlines()
keywords = ['openrouter', 'cloud', 'online', 'api_key', 'openai', 'cloud_enrich', 'CLOUD', 'ONLINE', 'ingest_online']
for i, line in enumerate(lines, 1):
    if any(k.lower() in line.lower() for k in keywords):
        print(f'{i:4}: {line}', end='')

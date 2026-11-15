
import requests
import xml.etree.ElementTree as ET

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

def list_objects(prefix, limit=25):
    token = None
    count = 0
    shown = 0
    total_bytes = 0

    print(f"\n{'=' * 65}")
    print("FOLDER:", prefix)
    print("=" * 65)

    while True:
        params = {
            "list-type": "2",
            "prefix": prefix,
            "max-keys": "1000",
        }

        if token:
            params["continuation-token"] = token

        response = requests.get(BASE, params=params, timeout=60)
        response.raise_for_status()

        root = ET.fromstring(response.content)

        for item in root.findall(".//s3:Contents", NS):
            key = item.findtext("s3:Key", namespaces=NS)
            size = int(item.findtext("s3:Size", default="0", namespaces=NS))

            count += 1
            total_bytes += size

            if shown < limit:
                print(f"{size:>12,} bytes  {key}")
                shown += 1

        truncated = root.findtext(
            "s3:IsTruncated",
            namespaces=NS
        ) == "true"

        if not truncated:
            break

        token = root.findtext(
            "s3:NextContinuationToken",
            namespaces=NS
        )

    print(f"\nTotal objects: {count:,}")
    print(f"Total size: {total_bytes / (1024**2):,.2f} MB")

def list_root_folders():
    response = requests.get(
        BASE,
        params={
            "list-type": "2",
            "delimiter": "/",
            "max-keys": "1000",
        },
        timeout=60,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)

    print("\nTOP-LEVEL BUCKET FOLDERS")
    for item in root.findall(".//s3:CommonPrefixes/s3:Prefix", NS):
        print(item.text)

print("Inspecting SPHEREx archive...")
list_root_folders()

for folder in [
    "qr3/spectral_channels/",
    "qr3/spectral_wcs/",
    "qr3/sip/",
]:
    list_objects(folder)


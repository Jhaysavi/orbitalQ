
import requests
import xml.etree.ElementTree as ET

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
PREFIXES = [
    "dr1/hips5_cube/hips_20261026/Norder5/Dir0/",
    "dr1/hips5_cube/hips_20261026/Norder5/Dir10000/",
]

NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

def inspect_directory(prefix):
    print(f"\n{'=' * 65}")
    print(f"DIRECTORY: {prefix}")
    print("=" * 65)

    params = {
        "list-type": "2",
        "prefix": prefix,
        "delimiter": "/",
        "max-keys": "1000",
    }

    response = requests.get(BASE, params=params, timeout=60)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    files = root.findall(".//s3:Contents", NS)
    directories = root.findall(".//s3:CommonPrefixes/s3:Prefix", NS)

    print(f"Files returned: {len(files)}")
    print(f"Subdirectories returned: {len(directories)}")

    print("\nFirst 15 files:")
    for item in files[:15]:
        key = item.find("s3:Key", NS).text
        size = int(item.find("s3:Size", NS).text)
        print(f"{size:>12,} bytes  {key}")

    print("\nFirst 10 subdirectories:")
    for item in directories[:10]:
        print(item.text)

    print("\nListing truncated:", root.findtext("s3:IsTruncated", namespaces=NS))

for prefix in PREFIXES:
    inspect_directory(prefix)

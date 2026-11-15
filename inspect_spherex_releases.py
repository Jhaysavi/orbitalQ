
import requests
import xml.etree.ElementTree as ET

BASE = "https://nasa-irsa-spherex.s3.us-east-1.amazonaws.com/"
NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

def inspect_prefix(prefix):
    params = {
        "list-type": "2",
        "prefix": prefix,
        "delimiter": "/",
        "max-keys": "1000",
    }

    response = requests.get(BASE, params=params, timeout=60)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    folders = [
        x.text for x in root.findall(
            ".//s3:CommonPrefixes/s3:Prefix", NS
        )
    ]

    files = [
        (x.find("s3:Key", NS).text,
         int(x.find("s3:Size", NS).text))
        for x in root.findall(".//s3:Contents", NS)
    ]

    return folders, files


for release in ["dr1/", "qr2/", "qr3/"]:
    print("\n" + "=" * 65)
    print("RELEASE:", release)
    print("=" * 65)

    folders, files = inspect_prefix(release)

    print("\nSUBFOLDERS:")
    for folder in folders:
        print(" ", folder)

    print("\nDIRECT FILES:")
    for key, size in files:
        print(f"  {size:>12,} bytes  {key}")

    print("\nNumber of subfolders:", len(folders))
    print("Number of direct files:", len(files))

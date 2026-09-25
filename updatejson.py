import os
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError


# ==========================================================
# CONFIGURATION
# ==========================================================

GRADLE_URL = (
    "https://raw.githubusercontent.com/"
    "soctrungkien/ZaliaBetter/main/"
    "ZalithLauncher/gradle.properties"
)

RELEASE_API_URL = (
    "https://api.github.com/repos/"
    "soctrungkien/ZaliaBetter/releases/tags/{tag}"
)

OUTPUT_DIR = Path("v2")


# ==========================================================
# HOTFIX
# ==========================================================

# GitHub Actions:
#
# APK_HOTFIX=on
#     -> ZaliaBetter-x.xx_hotfix.apk
#
# APK_HOTFIX=off
#     -> ZaliaBetter-x.xx.apk

HOTFIX = (
    os.environ
    .get("APK_HOTFIX", "off")
    .strip()
    .lower()
    == "on"
)

APK_SUFFIX = "_hotfix" if HOTFIX else ""


# ==========================================================
# DOWNLOAD TEXT
# ==========================================================

def download_text(url: str) -> str:
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urlopen(req) as response:
        return response.read().decode("utf-8")


# ==========================================================
# GET FILE SIZE
# ==========================================================

def get_file_size(url: str) -> int:
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            },
            method="HEAD"
        )

        with urlopen(req) as response:
            content_length = response.headers.get(
                "Content-Length",
                "0"
            )

            return int(content_length)

    except HTTPError as error:
        print(
            f"  Failed to check file size "
            f"(HTTP {error.code}): {url}"
        )

        return 0

    except Exception as error:
        print(
            f"  Failed to check file size: {error}"
        )

        return 0


# ==========================================================
# PARSE GRADLE PROPERTIES
# ==========================================================

def parse_properties(text: str) -> dict[str, str]:
    props: dict[str, str] = {}

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        props[key.strip()] = value.strip()

    return props


# ==========================================================
# MARKDOWN -> CHUNKS
# ==========================================================

def markdown_to_chunks(
    markdown_text: str
) -> list[dict]:

    chunks: list[dict] = []

    current_chunk: dict | None = None

    lines = markdown_text.splitlines()

    for raw_line in lines:
        line = raw_line.rstrip()

        if not line.strip():
            continue

        # --------------------------------------------------
        # Heading
        # --------------------------------------------------

        heading_match = re.match(
            r"^(#{1,6})\s+(.+)$",
            line
        )

        if heading_match:
            title = heading_match.group(2).strip()

            current_chunk = {
                "title": title,
                "texts": []
            }

            chunks.append(current_chunk)

            continue

        # --------------------------------------------------
        # Text before first heading
        # --------------------------------------------------

        if current_chunk is None:
            current_chunk = {
                "title": "Release Notes",
                "texts": []
            }

            chunks.append(current_chunk)

        # --------------------------------------------------
        # Indentation
        # --------------------------------------------------

        indentation = 0

        if line.startswith("  - "):
            indentation = 1
            line = line[4:]

        elif line.startswith("- "):
            line = line[2:]

        # --------------------------------------------------
        # Markdown links
        # --------------------------------------------------

        links = []

        for text, link in re.findall(
            r"\[([^\]]+)\]\(([^)]+)\)",
            line
        ):
            links.append(
                {
                    "text": text,
                    "link": link
                }
            )

        # --------------------------------------------------
        # Clean markdown links
        # --------------------------------------------------

        clean_text = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r"\1",
            line
        ).strip()

        text_obj = {
            "text": clean_text
        }

        if indentation > 0:
            text_obj["indentation"] = indentation

        if links:
            text_obj["links"] = links

        current_chunk["texts"].append(
            text_obj
        )

    return chunks


# ==========================================================
# GET GITHUB RELEASE DATA
# ==========================================================

def get_release_data(version: str) -> dict:
    url = RELEASE_API_URL.format(
        tag=version
    )

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/vnd.github+json"
        }
    )

    with urlopen(req) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


# ==========================================================
# DOWNLOAD GRADLE.PROPERTIES
# ==========================================================

print(
    "Downloading gradle.properties..."
)

gradle_text = download_text(
    GRADLE_URL
)

props = parse_properties(
    gradle_text
)


# ==========================================================
# READ PROJECT INFORMATION
# ==========================================================

LAUNCHER_NAME = props.get(
    "launcher_name",
    "ZaliaBetter"
)

APP_NAME = props.get(
    "launcher_app_name",
    "Zalia Better"
)

SHORT_NAME = props.get(
    "launcher_short_name",
    "ZB"
)

HOME_URL = props.get(
    "url_home",
    "https://github.com/soctrungkien/ZaliaBetter"
)

VERSION = props.get(
    "launcher_version_name",
    "0.0.0"
)

VERSION_CODE = int(
    props.get(
        "launcher_version_code",
        "1"
    )
)


# ==========================================================
# RELEASE URL
# ==========================================================

BASE_RELEASE_URL = (
    f"{HOME_URL}/releases/download/{VERSION}"
)


# ==========================================================
# RELEASE DATA
# ==========================================================

print(
    f"Downloading release data for tag: {VERSION}"
)

release_data = get_release_data(
    VERSION
)

release_body = release_data.get(
    "body",
    ""
)

created_at = release_data.get(
    "published_at",
    ""
)


# ==========================================================
# FILE ENTRY
# ==========================================================

def create_file_entry(
    filename: str,
    arch: str
) -> dict:

    file_url = (
        f"{BASE_RELEASE_URL}/{filename}"
    )

    print(
        f"Checking size: {filename}"
    )

    size = get_file_size(
        file_url
    )

    return {
        "file_name": filename,
        "uri": file_url,
        "arch": arch,
        "size": size
    }


# ==========================================================
# APK FILES
# ==========================================================

files = [
    create_file_entry(
        f"{LAUNCHER_NAME}-{VERSION}-arm64-v8a.apk",
        "arm64"
    ),

    create_file_entry(
        f"{LAUNCHER_NAME}-{VERSION}-armeabi-v7a.apk",
        "arm"
    ),

    create_file_entry(
        f"{LAUNCHER_NAME}-{VERSION}-x86.apk",
        "x86"
    ),

    create_file_entry(
        f"{LAUNCHER_NAME}-{VERSION}-x86_64.apk",
        "x86_64"
    ),

    create_file_entry(
        f"{LAUNCHER_NAME}-{VERSION}{APK_SUFFIX}.apk",
        "all"
    )
]


# ==========================================================
# BASE JSON
# ==========================================================

base_json = {
    "code": VERSION_CODE,

    "version": VERSION,

    "created_at": created_at,

    "default_cloud_drive": {
        "language": "en",

        "link": f"{HOME_URL}/releases",

        "links": [
            {
                "name": "GitHub Releases",

                "link": f"{HOME_URL}/releases"
            }
        ]
    },

    "files": files
}


# ==========================================================
# LATEST VERSION JSON
# ==========================================================

latest_version = deepcopy(
    base_json
)

latest_version["default_body"] = {
    "language": "en",

    "chunks": markdown_to_chunks(
        release_body
    )
}

latest_version["bodies"] = []


# ==========================================================
# LATEST VERSION MARKDOWN JSON
# ==========================================================

latest_version_md = deepcopy(
    base_json
)

latest_version_md["default_body"] = {
    "language": "en",

    "markdown": release_body
}

latest_version_md["bodies"] = []


# ==========================================================
# OUTPUT DIRECTORY
# ==========================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ==========================================================
# OUTPUT FILES
# ==========================================================

latest_version_path = (
    OUTPUT_DIR / "latest_version.json"
)

latest_version_md_path = (
    OUTPUT_DIR / "latest_version_md.json"
)


# ==========================================================
# WRITE latest_version.json
# ==========================================================

with open(
    latest_version_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        latest_version,
        f,
        ensure_ascii=False,
        indent=4
    )


# ==========================================================
# WRITE latest_version_md.json
# ==========================================================

with open(
    latest_version_md_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        latest_version_md,
        f,
        ensure_ascii=False,
        indent=4
    )


# ==========================================================
# RESULT
# ==========================================================

print()

print(
    f"Launcher: {APP_NAME}"
)

print(
    f"Short Name: {SHORT_NAME}"
)

print(
    f"Version: {VERSION}"
)

print(
    f"Version Code: {VERSION_CODE}"
)

print(
    f"Created At: {created_at}"
)

print(
    f"Hotfix: {'ON' if HOTFIX else 'OFF'}"
)

print(
    f"APK Suffix: {APK_SUFFIX or '(none)'}"
)

print()

print("Generated:")

print(
    f" - {latest_version_path}"
)

print(
    f" - {latest_version_md_path}"
)

print()

print("APK files:")

for file_info in files:
    print(
        f" - {file_info['file_name']} "
        f"({file_info['size']} bytes)"
    )

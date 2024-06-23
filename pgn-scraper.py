#!/usr/bin/env python3

import time
import requests
from re import sub
from os import path, makedirs
from urllib.parse import unquote
from unicodedata import normalize
from secrets import token_urlsafe
from string import ascii_letters, digits
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup, SoupStrainer
from concurrent.futures import ThreadPoolExecutor, as_completed

chess_files = (
    ".pgn",
    ".zip",
    ".cbv",
    ".cbz",
    ".cbf",
    ".7z",
    ".s7z",
    ".zz",
    ".si4",
    ".sn4",
    ".sg4",
    ".epd",
    ".cbb",
    ".cbh",
    ".cbt",
    "download=1",
)

failed_urls = dict()
session = requests.Session()

# Inspired by Django's utils.text.py
def sanitize_filename(value, allow_unicode=False):
    if value:
        value = unquote(str(value))
        if allow_unicode:
            ascii_value = normalize("NFKC", value)
        else:
            ascii_value = (normalize("NFKD", value).encode("ascii", "ignore").decode("ascii"))
        valid_chars = "-_.()'&! %s%s" % (ascii_letters, digits)
        lower = ascii_value.lower().strip().replace(" ", "-")
        valid = "".join(c for c in lower if c in valid_chars)
        output = sub(r"[-\s]+", "-", valid).strip("-")
        if not output.split(".", -1)[0]:
            output = f"generated_{token_urlsafe(5)}{output}"
        if output in {"", ".", "..", "-"}:
            output = f"generated_{token_urlsafe(5)}"
        return output
    else:
        return f"generated_{token_urlsafe(5)}"


def url_to_dir(url):
    host = urlparse(url).netloc
    if host.startswith("www."):
        host = host[4:]
    return host

def get_files(html):
    try:
        links = set()
        link_strainer = SoupStrainer("a")
        soup = BeautifulSoup(html, "lxml", parse_only=link_strainer)
        for link in soup.find_all("a", href=True):
            href = link.get("href")
            if href and href.endswith(chess_files):
                links.add(href)
        return links
    except Exception as err:
        print(err)
        return set()

def fetch_and_parse(url):
    links = set()
    try:
        response = session.get(url, headers=headers)
        if response.status_code == 200:
            links.update(get_files(response.text))
            for element in ["frame", "iframe"]:
                frames_strainer = SoupStrainer(element)
                frames = BeautifulSoup(
                    response.text, "lxml", parse_only=frames_strainer
                ).find_all(element)
                for frame in frames:
                    frame_src = frame.get("src")
                    if frame_src:
                        if not frame_src.startswith("http"):
                            frame_src = urljoin(url, frame_src)
                        frame_response = session.get(frame_src)
                        if frame_response.status_code == 200:
                            links.update(get_files(frame_response.text))
        elif response.status_code != 404:
            failed_urls[url] = response.status_code
            print(f"failed parsing {url}: {response.status_code}")
    except Exception as err:
        print(f"Error occurred fetching: {url}, {err}")
        return set()
    return links


def download_file(url, link):
    if not link.startswith("http"):
        link = urljoin(url, link)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = session.get(link, headers=headers)
            if response.status_code == 200:
                break
            elif response.status_code == 404:
                failed_urls[link] = 404
                print(f"{link} Not Found!")
                return
            else:
                failed_urls[link] = response.status_code
        except Exception as err:
            print(f"Error occurred fetching {link}: {err}")
            if attempt < max_retries - 1:
                time.sleep(2**attempt)
            else:
                return

    filename = link.split("/")[-1]
    file_dir = sanitize_filename(url_to_dir(url))
    makedirs(file_dir, exist_ok=True)

    if "content-disposition" in response.headers:
        content_disposition = response.headers["content-disposition"]
        filename = content_disposition.split("filename=")[1]

    filename = sanitize_filename(filename)
    makedirs(sanitize_filename(file_dir), exist_ok=True)
    full_file_path = path.join(file_dir, filename)
    with open(full_file_path, "wb") as file:
        file.write(response.content)
        print(f"Downloaded file {filename}")


def thread_downloads(host_url, links):
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(download_file, host_url, link) for link in links]
        try:
            for future in as_completed(futures):
                future.result()
        except KeyboardInterrupt:
            print("Interrupted, attempting to stop threads.")
            executor.shutdown(wait=True, cancel_futures=True)
            print("Threads stopped.")


if __name__ == "__main__":
    urls_to_parse = ["https://www.pgnmentor.com/files.html"]
    for host_url in urls_to_parse:

        headers = {
            "Host": urlparse(host_url).netloc,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Cache-Control": "max-age=0",
            "Upgrade-Insecure-Requests": "1",
        }

        links = [host_url]
        if not host_url.endswith(chess_files):
            links = fetch_and_parse(host_url)
        if len(links) == 0:
            print(f"No chess files found on {host_url}")
            continue
        else:
            thread_downloads(host_url, links)

    with open("failed_urls", "w") as file:
        file.write("\n".join(failed_urls))
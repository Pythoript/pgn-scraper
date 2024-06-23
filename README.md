# pgn-scraper
Scrape the contents of a single webpage or list of pages for chess files (pgn, cbv, etc.), download them, and organize them into directories based on the website's domain name.

## Usage

Simply add the URLs you want to scrape to `urls_to_parse` and you're set to go.

## Known issues and limitations

- pgn-scraper is unable to differentiate between archives that contain pgns and those that don't.
- Implementation for scraping iframes seems unrelable
- If files in two different directories share the same name, the older file is overwritten

## TODO

- Seperate handaling of iframes
- fix overwiting bug
- Replace print statements with logging
- Update `get_files` to collect same-domain links and queue
for scraping

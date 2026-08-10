# Data Sources

The updater requests one Axi daily page per date and uses a descriptive
User-Agent with retries. It parses paper nodes with BeautifulSoup rather than
regular expressions. Selected IDs are sent to the arXiv Atom API in batches;
the updater does not download or mirror PDFs.

The generated record retains `axi_url`, `arxiv_url`, source mode, and filter
version so a future contributor can audit how a paper entered the archive.


from typing import Literal, List

scrape_types = Literal["markdown", "screenshot"]


def get_scrape_options(formats: List[scrape_types] = ["markdown"]):
    return {
        "type": "object",
        "description": "The options for the scrape",
        "properties": {
            "formats": {
                "type": "array",
                "description": "The format of the content to scrape",
                "items": {
                    "type": "string",
                    "enum": formats,
                },
            },
            "include_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "An array of HTML tags, classes, or IDs to include in the scraped content. Only elements matching these selectors will be returned.",
            },
            "exclude_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "An array of HTML tags, classes, or IDs to exclude from the scraped content. Elements matching these selectors will be omitted from the response.",
            },
            "only_main_content": {
                "type": "boolean",
                "description": "Whether to only return the main content of the page. If true, only the main content of the page will be returned, excluding any headers, navigation menus,footers, or other non-main content.",
            },
        },
        "required": [
            "include_tags",
            "exclude_tags",
            "only_main_content",
            "formats",
        ],
        "additionalProperties": False,
    }


SCRAPE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL of the website to scrape",
        },
        "scrape_options": get_scrape_options(),
    },
    "required": ["url", "scrape_options"],
    "additionalProperties": False,
}

SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL of the website to scrape",
        },
        "scrape_options": get_scrape_options(["screenshot"]),
    },
    "required": ["url", "scrape_options"],
    "additionalProperties": False,
}

CRAWL_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {
            "type": "string",
            "description": "The URL of the website to crawl",
        },
        "max_pages": {
            "type": "number",
            "description": "The maximum number of pages to crawl",
        },
        "follow_links": {
            "type": "boolean",
            "description": "Whether to follow links on the page",
        },
        "ignore_sitemap": {
            "type": "boolean",
            "description": "Whether to ignore the sitemap",
        },
        "exclude_patterns": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "An array of regular expressions or wildcard patterns specifying which URLs should be excluded from the crawl. Any pages whose URLs' path match one of these patterns will be skipped. Example: ['/admin', '/careers/*']",
        },
        "include_patterns": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "An array of regular expressions or wildcard patterns specifying which URLs should be included in the crawl. Only pages whose URLs' path match one of these path patterns will be visited. Example: ['/admin', '/careers/*']",
        },
        "scrape_options": get_scrape_options(),
    },
    "required": [
        "url",
        "max_pages",
        "follow_links",
        "ignore_sitemap",
        "exclude_patterns",
        "include_patterns",
        "scrape_options",
    ],
    "additionalProperties": False,
}

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "urls": {
            "type": "array",
            "items": {
                "type": "string",
            },
            "description": "A required list of up to 10 urls you want to process IN A SINGLE EXTRACTION. When answering questions that involve multiple sources or topics, ALWAYS include ALL relevant URLs in this single array rather than making separate function calls. This enables cross-referencing information across multiple sources to provide comprehensive answers. To allow crawling for any of the urls provided in the list, simply add /* to the end of the url (https://hyperbrowser.ai/*). This will crawl other pages on the site with the same origin and find relevant pages to use for the extraction context.",
        },
        "prompt": {
            "type": "string",
            "description": "A prompt describing how you want the data structured, or what you want to extract from the urls provided. Can also be used to guide the extraction process. For multi-source queries, structure this prompt to request unified, comparative, or aggregated information across all provided URLs.",
        },
        "schema": {
            "type": "string",
            "description": "A strict json schema you want the returned data to be structured as. For multi-source extraction, design this schema to accommodate information from all URLs in a single structure. Ensure that this is a proper json schema, and the root level should be of type 'object'.",
        },
        "max_links": {
            "type": "number",
            "description": "The maximum number of links to look for if performing a crawl for any given url in the urls list.",
        },
    },
    "required": ["urls", "prompt", "schema", "max_links"],
    "additionalProperties": False,
}

BROWSER_USE_LLM_SCHEMA = {
    "type": "string",
    "enum": [
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "gemini-2.0-flash",
    ],
    "default": "gemini-2.0-flash",
}

BROWSER_USE_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {
            "type": "string",
            "description": "The text description of the task to be performed by the agent.",
        },
        "llm": {
            **BROWSER_USE_LLM_SCHEMA,
            "description": "The language model (LLM) instance to use for generating actions. Default to gemini-2.0-flash.",
        },
        "planner_llm": {
            **BROWSER_USE_LLM_SCHEMA,
            "description": "The language model to use specifically for planning future actions, can differ from the main LLM. Default to gemini-2.0-flash.",
        },
        "page_extraction_llm": {
            **BROWSER_USE_LLM_SCHEMA,
            "description": "The language model to use for extracting structured data from webpages. Default to gemini-2.0-flash.",
        },
        "keep_browser_open": {
            "type": "boolean",
            "description": "When enabled, keeps the browser session open after task completion.",
        },
    },
    "required": [
        "task",
        "llm",
        "planner_llm",
        "page_extraction_llm",
        "keep_browser_open",
    ],
    "additionalProperties": False,
}

FILL_CREDENTIAL_DESCRIPTION = (
    "Fill a stored login credential into the browser session's page by typing "
    "its values into the inputs you select. A credential is a saved login (for "
    "example a username and password) that you refer to by name; you never see "
    "its values, and they never appear in this tool's input or output. This tool "
    "only types: it does NOT submit the form. After a fill, click the login "
    "button or press Enter with your other browser tools.\n\n"
    "The result is JSON with the origin and pageId of the page that was filled, "
    "and an outcome for each field:\n"
    "- filled: the input now holds the value.\n"
    "- not_found: no input matched the selector. Look at the page again and fix "
    "the selector; the form may not have loaded yet, or it may be inside an "
    "iframe (pass frame_url).\n"
    "- ambiguous: several visible inputs matched. Use a more specific selector.\n"
    "- not_editable: the input is disabled, read-only, hidden or not a text "
    "input. Select the real input, or reveal it first (some sites show the "
    "password input only after the username step).\n"
    "- not_accepted: the page did not keep the value (for example a length "
    "limit). Check that you selected the right input.\n"
    "- not_populated: the stored credential has no such field. Check the field "
    "name; common ones are username, email and password.\n"
    "Filling again is safe. Errors come back as JSON with a code, for example "
    '{"error": {"code": "CREDENTIAL_PAGE_AMBIGUOUS", "message": "...", '
    '"retryable": false, "details": {"pages": [...]}}}. On '
    "CREDENTIAL_PAGE_AMBIGUOUS, call again with page_id set to the pageId of the "
    "tab that shows the login form. CREDENTIAL_ORIGIN_NOT_ALLOWED means the "
    "credential may not be used on this site; do not retry it there. When "
    "retryable is true, the same call may succeed if you try again."
)

FILL_CREDENTIAL_SCHEMA = {
    "type": "object",
    "properties": {
        "credential": {
            "type": "string",
            "description": "The name of the stored credential to fill, as you were "
            "told it. You cannot see its values; refer to it only by name.",
        },
        "fields": {
            "type": "array",
            "description": "The inputs to fill: one entry per credential field, "
            "each field at most once.",
            "minItems": 1,
            "maxItems": 16,
            "items": {
                "type": "object",
                "properties": {
                    "field": {
                        "type": "string",
                        "description": "The credential field to type: a key of "
                        'the stored login such as "username", "email" or '
                        '"password".',
                    },
                    "selector": {
                        "type": "string",
                        "description": "A CSS selector matching exactly one "
                        'visible input on the page, such as "#login_field" or '
                        "\"input[name='password']\".",
                    },
                },
                "required": ["field", "selector"],
                "additionalProperties": False,
            },
        },
        "page_id": {
            "type": ["string", "null"],
            "description": "The browser tab to fill. Use null unless a previous "
            "call failed with CREDENTIAL_PAGE_AMBIGUOUS; then pass the pageId of "
            "the tab showing the login form, from that error's details.pages.",
        },
        "frame_url": {
            "type": ["string", "null"],
            "description": "For a login form inside an iframe: the start of the "
            'iframe\'s URL, such as "https://login.example.com/". Use null when '
            "the form is in the page itself.",
        },
    },
    "required": ["credential", "fields", "page_id", "frame_url"],
    "additionalProperties": False,
}

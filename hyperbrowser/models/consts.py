from typing import Literal

ScrapeFormat = Literal["markdown", "html", "links", "screenshot"]

Country = Literal[
    "AD",
    "AE",
    "AF",
    "AL",
    "AM",
    "AO",
    "AR",
    "AT",
    "AU",
    "AW",
    "AZ",
    "BA",
    "BD",
    "BE",
    "BG",
    "BH",
    "BJ",
    "BO",
    "BR",
    "BS",
    "BT",
    "BY",
    "BZ",
    "CA",
    "CF",
    "CH",
    "CI",
    "CL",
    "CM",
    "CN",
    "CO",
    "CR",
    "CU",
    "CY",
    "CZ",
    "DE",
    "DJ",
    "DK",
    "DM",
    "EC",
    "EE",
    "EG",
    "ES",
    "ET",
    "EU",
    "FI",
    "FJ",
    "FR",
    "GB",
    "GE",
    "GH",
    "GM",
    "GR",
    "HK",
    "HN",
    "HR",
    "HT",
    "HU",
    "ID",
    "IE",
    "IL",
    "IN",
    "IQ",
    "IR",
    "IS",
    "IT",
    "JM",
    "JO",
    "JP",
    "KE",
    "KH",
    "KR",
    "KW",
    "KZ",
    "LB",
    "LI",
    "LR",
    "LT",
    "LU",
    "LV",
    "MA",
    "MC",
    "MD",
    "ME",
    "MG",
    "MK",
    "ML",
    "MM",
    "MN",
    "MR",
    "MT",
    "MU",
    "MV",
    "MX",
    "MY",
    "MZ",
    "NG",
    "NL",
    "NO",
    "NZ",
    "OM",
    "PA",
    "PE",
    "PH",
    "PK",
    "PL",
    "PR",
    "PT",
    "PY",
    "QA",
    "RANDOM_COUNTRY",
    "RO",
    "RS",
    "RU",
    "SA",
    "SC",
    "SD",
    "SE",
    "SG",
    "SI",
    "SK",
    "SN",
    "SS",
    "TD",
    "TG",
    "TH",
    "TM",
    "TN",
    "TR",
    "TT",
    "TW",
    "UA",
    "UG",
    "US",
    "UY",
    "UZ",
    "VE",
    "VG",
    "VN",
    "YE",
    "ZA",
    "ZM",
    "ZW",
    "ad",
    "ae",
    "af",
    "al",
    "am",
    "ao",
    "ar",
    "at",
    "au",
    "aw",
    "az",
    "ba",
    "bd",
    "be",
    "bg",
    "bh",
    "bj",
    "bo",
    "br",
    "bs",
    "bt",
    "by",
    "bz",
    "ca",
    "cf",
    "ch",
    "ci",
    "cl",
    "cm",
    "cn",
    "co",
    "cr",
    "cu",
    "cy",
    "cz",
    "de",
    "dj",
    "dk",
    "dm",
    "ec",
    "ee",
    "eg",
    "es",
    "et",
    "eu",
    "fi",
    "fj",
    "fr",
    "gb",
    "ge",
    "gh",
    "gm",
    "gr",
    "hk",
    "hn",
    "hr",
    "ht",
    "hu",
    "id",
    "ie",
    "il",
    "in",
    "iq",
    "ir",
    "is",
    "it",
    "jm",
    "jo",
    "jp",
    "ke",
    "kh",
    "kr",
    "kw",
    "kz",
    "lb",
    "li",
    "lr",
    "lt",
    "lu",
    "lv",
    "ma",
    "mc",
    "md",
    "me",
    "mg",
    "mk",
    "ml",
    "mm",
    "mn",
    "mr",
    "mt",
    "mu",
    "mv",
    "mx",
    "my",
    "mz",
    "ng",
    "nl",
    "no",
    "nz",
    "om",
    "pa",
    "pe",
    "ph",
    "pk",
    "pl",
    "pr",
    "pt",
    "py",
    "qa",
    "ro",
    "rs",
    "ru",
    "sa",
    "sc",
    "sd",
    "se",
    "sg",
    "si",
    "sk",
    "sn",
    "ss",
    "td",
    "tg",
    "th",
    "tm",
    "tn",
    "tr",
    "tt",
    "tw",
    "ua",
    "ug",
    "us",
    "uy",
    "uz",
    "ve",
    "vg",
    "vn",
    "ye",
    "za",
    "zm",
    "zw",
]

OperatingSystem = Literal["windows", "android", "macos", "linux", "ios"]

Platform = Literal["chrome", "firefox", "safari", "edge"]

ISO639_1 = Literal[
    "aa",
    "ab",
    "ae",
    "af",
    "ak",
    "am",
    "an",
    "ar",
    "as",
    "av",
    "ay",
    "az",
    "ba",
    "be",
    "bg",
    "bh",
    "bi",
    "bm",
    "bn",
    "bo",
    "br",
    "bs",
    "ca",
    "ce",
    "ch",
    "co",
    "cr",
    "cs",
    "cu",
    "cv",
    "cy",
    "da",
    "de",
    "dv",
    "dz",
    "ee",
    "el",
    "en",
    "eo",
    "es",
    "et",
    "eu",
    "fa",
    "ff",
    "fi",
    "fj",
    "fo",
    "fr",
    "fy",
    "ga",
    "gd",
    "gl",
    "gn",
    "gu",
    "gv",
    "ha",
    "he",
    "hi",
    "ho",
    "hr",
    "ht",
    "hu",
    "hy",
    "hz",
    "ia",
    "id",
    "ie",
    "ig",
    "ii",
    "ik",
    "io",
    "is",
    "it",
    "iu",
    "ja",
    "jv",
    "ka",
    "kg",
    "ki",
    "kj",
    "kk",
    "kl",
    "km",
    "kn",
    "ko",
    "kr",
    "ks",
    "ku",
    "kv",
    "kw",
    "ky",
    "la",
    "lb",
    "lg",
    "li",
    "ln",
    "lo",
    "lt",
    "lu",
    "lv",
    "mg",
    "mh",
    "mi",
    "mk",
    "ml",
    "mn",
    "mo",
    "mr",
    "ms",
    "mt",
    "my",
    "na",
    "nb",
    "nd",
    "ne",
    "ng",
    "nl",
    "nn",
    "no",
    "nr",
    "nv",
    "ny",
    "oc",
    "oj",
    "om",
    "or",
    "os",
    "pa",
    "pi",
    "pl",
    "ps",
    "pt",
    "qu",
    "rm",
    "rn",
    "ro",
    "ru",
    "rw",
    "sa",
    "sc",
    "sd",
    "se",
    "sg",
    "si",
    "sk",
    "sl",
    "sm",
    "sn",
    "so",
    "sq",
    "sr",
    "ss",
    "st",
    "su",
    "sv",
    "sw",
    "ta",
    "te",
    "tg",
    "th",
    "ti",
    "tk",
    "tl",
    "tn",
    "to",
    "tr",
    "ts",
    "tt",
    "tw",
    "ty",
    "ug",
    "uk",
    "ur",
    "uz",
    "ve",
    "vi",
    "vo",
    "wa",
    "wo",
    "xh",
    "yi",
    "yo",
    "za",
    "zh",
    "zu",
]

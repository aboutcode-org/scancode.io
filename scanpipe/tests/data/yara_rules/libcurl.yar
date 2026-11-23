rule libcurl_detection {
    meta:
        description = "Detects libcurl multiprotocol file transfer library"
        base_purl = "pkg:generic/libcurl"
        download_url = "https://github.com/ossf/cve-bin-tool/blob/main/cve_bin_tool/checkers/curl.py"
        copyright = "Copyright (C) 2023 Orange"
        license_expression = "GPL-3.0-or-later"
        notes = "Modified from the original Python code to convert to YARA format"
    strings:
        $version = /libcurl[ \-\/]([678]+\.[0-9]+\.[0-9]+)/
        $version_src = /LIBCURL_VERSION\s+"([678]+\.[0-9]+\.[0-9]+)"/
        $sym1 = "curl_easy_init" ascii
        $sym2 = "curl_easy_setopt" ascii
        $sym3 = "curl_easy_perform" ascii
        $sym4 = "curl_easy_cleanup" ascii
    condition:
        $version or $version_src or (2 of ($sym*))
}


rule jq_detection {
    meta:
        description = "Detects jq lightweight and flexible command-line JSON processor"
        base_purl = "pkg:generic/jq"
        download_url = "https://github.com/ossf/cve-bin-tool/blob/79cea25399500d8e8b1eb4ff550879a73d94d9c9/cve_bin_tool/checkers/jq.py"
        copyright = "Copyright (C) 2023 Orange"
        license_expression = "GPL-3.0-or-later"
        notes = "Modified from the original Python code to convert to YARA format"
    strings:
        $version = /jq-([0-9]+\.[0-9]+(\.[0-9]+)?)/
        $version_src = /AC_INIT\(\s*\[?jq\]?,\s*\[?([0-9]+\.[0-9]+(\.[0-9]+)?)\]?\)/
        $ver_prefix = "JQ_VERSION" ascii
        $ver_num = /[0-9]+\.[0-9]+(\.[0-9]+)?/
        $str1 = "jq - commandline JSON processor" ascii
        $str2 = "https://github.com/jqlang/jq" ascii
        $str3 = "https://stedolan.github.io/jq" ascii
        $sym1 = "jq_init" ascii
        $sym2 = "jq_compile" ascii
        $sym3 = "jq_teardown" ascii
        $sym4 = "jv_parse" ascii
    condition:
        $version or $version_src or ($ver_prefix and $ver_num) or (any of ($str*)) or (2 of ($sym*))
}


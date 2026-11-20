rule openssl_detection {
    meta:
        description = "Detects OpenSSL cryptography library"
        base_purl = "pkg:generic/openssl"
        download_url = "https://github.com/ossf/cve-bin-tool/blob/4e25ef14f6ec7f099c3e822afa0f8853b385d47e/cve_bin_tool/checkers/openssl.py"
        copyright = "Copyright (C) 2023 Orange"
        license_expression = "GPL-3.0-or-later"
        notes = "Modified from the original Python code to convert to YARA format"
    strings:
        $version = /OpenSSL ([0-9]+\.[0-9]+\.[0-9]+[a-z]*)/
        $version_src = /OPENSSL_VERSION_TEXT\s+"OpenSSL ([0-9]+\.[0-9]+\.[0-9]+[a-z]*)/
        $str1 = "part of OpenSSL" ascii
        $str2 = "openssl.cnf" ascii
        $str3 = "-DOPENSSL_" ascii
        $str4 = "OPENSSLDIR" ascii
        $sym1 = "SSL_CTX_new" ascii
        $sym2 = "SSL_connect" ascii
        $sym3 = "OpenSSL_add_all_ciphers" ascii
        $sym4 = "OPENSSL_init_ssl" ascii
    condition:
        $version or $version_src or (any of ($str*) and any of ($sym*)) or (2 of ($sym*))
}

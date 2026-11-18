rule libass_detection {
    meta:
        description = "Detects libass subtitle renderer library"
        base_purl = "pkg:generic/libass"
        download_url = "https://github.com/ossf/cve-bin-tool/blob/79cea25399500d8e8b1eb4ff550879a73d94d9c9/cve_bin_tool/checkers/libass.py"
        copyright = "Copyright (C) 2023 Orange"
        license_expression = "GPL-3.0-or-later"
        notes = "Modified from the original Python code to convert to YARA format"
    strings:
        $version = /([0-9]+\.[0-9]+\.[0-9]+)\r?\nlibass/
        $version_src = /AC_INIT\(\s*\[?libass\]?,\s*\[?([0-9]+\.[0-9]+(\.[0-9]+)?)\]?\)/
        $version_cl = /libass\s*\(([0-9]+\.[0-9]+(\.[0-9]+)?)\)/
        $sym1 = "ass_renderer_init" ascii
        $sym2 = "ass_library_init" ascii
        $sym3 = "ass_render_frame" ascii
    condition:
        $version or $version_src or $version_cl or (2 of ($sym*))
}


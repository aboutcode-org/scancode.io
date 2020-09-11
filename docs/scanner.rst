Scanner
=======

The `/api/scans/` API endpoint allows to run a ScanCode-toolkit Scan on a
provided public Download URL.

The file is downloaded, extracted, and scanned.
The results are then available from the REST API.

REST API
--------

cURL API requests examples::

    curl -H "Authorization: Token [API_TOKEN]" -X GET https://enterprise.scancode.io/api/scans/
    curl -H "Authorization: Token [API_TOKEN]" -X GET https://enterprise.scancode.io/api/scans/[SCAN_UUID]/
    curl -H "Authorization: Token [API_TOKEN]" -X POST -H "Content-Type: application/json" -d '{"uri": "[URI_TO_SCAN]"}' https://enterprise.scancode.io/api/scans/

Python requests examples::

    import requests
    payload = {'uri': '[URI_TO_SCAN]'}
    headers = {'Authorization': 'Token [API_TOKEN]'}
    r = requests.post('https://enterprise.scancode.io/api/scans/', headers=headers, data=payload)
    print(r.json())

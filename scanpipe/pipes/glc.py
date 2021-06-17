from LicenseClassifier.classifier import LicenseClassifier

def run_glc(location, output_file, search_subdir):
    """
    Scan `location` content and write results into `output_file`.
    """
    l = LicenseClassifier()
    l.catalogueDir(location, search_subdir, output_file)
    return

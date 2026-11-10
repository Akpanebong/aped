from django.utils.text import slugify
def safe_filename(name):
    return slugify(name)[:70] or 'aped-export'

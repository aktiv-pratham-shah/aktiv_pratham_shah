"""
Odoo Website Migration Script: v18 → v19
=========================================
Handles:
  - URL format: /web/image/ID-CHECKSUM/filename.ext
  - data-original-id="ID"
  - ALL image types (binary, url)
  - All pages, views, menus, custom CSS

Run: python3 sync_website_18_to_19.py
"""

import xmlrpc.client
import logging
import re
import sys
import time

# ==============================================================================
# CONFIGURATION — Update these values only
# ==============================================================================
SRC_URL  = 'http://localhost:8081'
SRC_DB   = 'tahel_4_june'
SRC_USER = 'admin'
SRC_PASS = 'admin'
SRC_WEBSITE_ID = 1

DST_URL  = 'http://localhost:8082'
DST_DB   = 'tahel_4_june_1'
DST_USER = 'admin'
DST_PASS = 'admin'
DST_WEBSITE_ID = 1

TIMEOUT    = 180
BATCH_SIZE = 10   # Reduce to 5 or 3 if you still hit MemoryError on large images
# ==============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# XML-RPC Helpers
# ──────────────────────────────────────────────────────────────────────────────

def make_proxy(url):
    t = xmlrpc.client.Transport()
    t.timeout = TIMEOUT
    return xmlrpc.client.ServerProxy(url, transport=t)


def connect(url, db, user, password):
    try:
        common = make_proxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, user, password, {})
        if not uid:
            log.error(f"  Authentication FAILED for {url} / {db}")
            return None
    except Exception as e:
        log.error(f"  Connection FAILED for {url} / {db}: {e}")
        return None

    obj_proxy = make_proxy(f'{url}/xmlrpc/2/object')

    class Model:
        def __call__(self, model, method, args, kwargs=None):
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return obj_proxy.execute_kw(db, uid, password, model, method, args, kwargs or {})
                except Exception as e:
                    if attempt < max_retries - 1:
                        log.warning(f"  [Retry {attempt+1}/{max_retries}] XML-RPC Error on {model}.{method}: {e}")
                        time.sleep(2)
                    else:
                        log.error(f"  [FAILED] XML-RPC Error on {model}.{method} after {max_retries} attempts: {e}")
                        # Return safe defaults to avoid tracebacks downstream
                        if method in ('search', 'search_read', 'read'):
                            return []
                        elif method == 'create':
                            return False
                        return False

    log.info(f"  Connected → {url} / {db}  (uid={uid})")
    return Model()


# ──────────────────────────────────────────────────────────────────────────────
# Step 1 – Collect all attachment IDs referenced in ANY page HTML
# ──────────────────────────────────────────────────────────────────────────────

def collect_referenced_attachment_ids(src):
    """
    Scan all ir.ui.view arch_db HTML and collect every attachment ID
    that appears in /web/image/<ID> or data-original-id="<ID>" patterns.
    """
    log.info("  Scanning all view HTML for referenced attachment IDs ...")

    # Pull ALL QWeb views (website pages use type=qweb)
    views = src('ir.ui.view', 'search_read',
                [[('type', '=', 'qweb')]],
                {'fields': ['id', 'arch_db']})

    ids_found = set()
    for v in views:
        html = v.get('arch_db') or ''
        # Pattern 1: /web/image/995 or /web/content/995
        for m in re.finditer(r'/web/(image|content)/(\d+)', html):
            ids_found.add(int(m.group(2)))
        # Pattern 2: data-original-id="995"
        for m in re.finditer(r'data-original-id=["\'](\d+)["\']', html):
            ids_found.add(int(m.group(1)))

    log.info(f"  Found {len(ids_found)} unique attachment IDs referenced in HTML: {sorted(ids_found)}")
    return ids_found


# ──────────────────────────────────────────────────────────────────────────────
# Step 2 – Migrate all images from v18 → v19, return {old_id: new_id}
# ──────────────────────────────────────────────────────────────────────────────

def migrate_images(src, dst, required_ids):
    """
    Fetches image metadata first (no binary data), then uploads in small
    batches to avoid XML-RPC MemoryError on large datasets.

    Returns {old_attachment_id: new_attachment_id}
    """
    log.info("  Fetching image attachment metadata from v18 ...")

    # ── Step A: Fetch metadata only (no datas) for binary files (images, videos, pdfs)
    all_meta = src('ir.attachment', 'search_read',
                   [[('type', '=', 'binary'),
                     '|', '|', ('mimetype', '=like', 'image/%'),
                               ('mimetype', '=like', 'video/%'),
                               ('mimetype', '=', 'application/pdf')]],
                   {'fields': ['id', 'name', 'mimetype', 'checksum', 'public',
                               'res_model', 'res_field']})
    log.info(f"  Found {len(all_meta)} media attachments in v18.")

    # Also get metadata for any required_ids not covered above (URL-type, etc.)
    if required_ids:
        existing_ids = {a['id'] for a in all_meta}
        missing_required = list(required_ids - existing_ids)
        if missing_required:
            extra_meta = src('ir.attachment', 'search_read',
                             [[('id', 'in', missing_required)]],
                             {'fields': ['id', 'name', 'mimetype', 'checksum', 'public',
                                         'res_model', 'res_field', 'type']})
            all_meta.extend(extra_meta)

    log.info(f"  Total attachments to process: {len(all_meta)}")

    # ── Step B: Build checksum index on destination to skip duplicates
    dst_existing = dst('ir.attachment', 'search_read',
                       [[('type', '=', 'binary'),
                         '|', '|', ('mimetype', '=like', 'image/%'),
                                   ('mimetype', '=like', 'video/%'),
                                   ('mimetype', '=', 'application/pdf')]],
                       {'fields': ['id', 'checksum']})
    dst_by_checksum = {r['checksum']: r['id'] for r in dst_existing if r.get('checksum')}

    id_map     = {}   # {old_id: new_id}
    meta_by_id = {}

    # ── Step C: Separate already-mapped (by checksum) from those needing upload
    ids_to_fetch = []
    for img in all_meta:
        old_id   = img['id']
        checksum = img.get('checksum')
        meta_by_id[old_id] = img

        if checksum and checksum in dst_by_checksum:
            id_map[old_id] = dst_by_checksum[checksum]
            if old_id in required_ids:
                log.info(f"    [{old_id}] '{img['name'][:45]}' → reused [{id_map[old_id]}]")
        else:
            ids_to_fetch.append(old_id)

    log.info(f"  {len(ids_to_fetch)} images need uploading, "
             f"fetching binary data in batches of {BATCH_SIZE} ...")

    # ── Step D: Batch-fetch datas and upload to destination
    total_batches = (len(ids_to_fetch) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num, batch_start in enumerate(range(0, len(ids_to_fetch), BATCH_SIZE), start=1):
        batch_ids = ids_to_fetch[batch_start: batch_start + BATCH_SIZE]
        log.info(f"  Batch {batch_num}/{total_batches}: fetching IDs {batch_ids} ...")

        try:
            batch_data = src('ir.attachment', 'read',
                             [batch_ids],
                             {'fields': ['id', 'datas']})
        except Exception as e:
            log.error(f"  Batch fetch FAILED for {batch_ids}: {e}")
            continue

        datas_by_id = {r['id']: r.get('datas') for r in batch_data}

        for old_id in batch_ids:
            img   = meta_by_id[old_id]
            datas = datas_by_id.get(old_id)

            if not datas:
                log.warning(f"    [{old_id}] '{img['name'][:45]}' → no binary data, skipping.")
                continue

            try:
                new_id = dst('ir.attachment', 'create', [{
                    'name':      img['name'],
                    'mimetype':  img.get('mimetype') or 'image/png',
                    'datas':     datas,
                    'public':    True,
                    'res_model': 'ir.ui.view',
                    'res_field': False,
                }])
                id_map[old_id] = new_id
                checksum = img.get('checksum')
                if checksum:
                    dst_by_checksum[checksum] = new_id
                log.info(f"    [{old_id}] '{img['name'][:45]}' → created [{new_id}]")
            except Exception as e:
                log.error(f"    [{old_id}] '{img['name'][:45]}' → FAILED: {e}")

    log.info(f"  Image migration done. {len(id_map)} mapped.")
    return id_map


# ──────────────────────────────────────────────────────────────────────────────
# Step 3 – Rewrite HTML: replace ALL old IDs with new IDs
# ──────────────────────────────────────────────────────────────────────────────

def rewrite_html(html, id_map):
    """
    Rewrites image IDs in HTML covering all Odoo patterns:

      /web/image/995                        → /web/image/1141
      /web/image/995-abc123/name.webp       → /web/image/1141/name.webp
      data-original-id="995"               → data-original-id="1141"
      data-img-id="995"                    → data-img-id="1141"
      data-media-id="995"                  → data-media-id="1141"
    """
    if not html:
        return html

    # ── Pattern 1: /web/image/<ID> or /web/content/<ID>
    #    Keeps everything AFTER the ID (slash, filename, query, etc.)
    def replace_img_url(m):
        endpoint = m.group(1)
        old_id   = int(m.group(2))
        suffix   = m.group(3) or ''   # could be "-abc123"  or ""
        rest     = m.group(4) or ''   # "/filename.webp?..."  or ""
        new_id   = id_map.get(old_id)
        if new_id:
            return f'/web/{endpoint}/{new_id}{rest}'
        return m.group(0)

    # Matches /web/image/995, /web/image/995-abc123, /web/image/995-abc123/filename.ext
    # AND /web/content/995...
    html = re.sub(
        r'/web/(image|content)/(\d+)(-[a-f0-9]+)?((?:/[^"\'\s]*)?)',
        replace_img_url,
        html
    )

    # ── Pattern 2: data-*-id="old_id"
    def replace_attr_id(m):
        attr_name = m.group(1)
        old_id    = int(m.group(2))
        new_id    = id_map.get(old_id)
        repl_id   = new_id if new_id else old_id
        return f'{attr_name}="{repl_id}"'

    html = re.sub(
        r'(data-original-id|data-img-id|data-media-id)=["\'](\d+)(["\'])',
        replace_attr_id,
        html
    )

    return html


# ──────────────────────────────────────────────────────────────────────────────
# Step 4a – Migrate Website Configuration
# ──────────────────────────────────────────────────────────────────────────────

def migrate_website_config(src, dst):
    log.info("  Fetching website configuration ...")
    try:
        src_web = src('website', 'read', [[SRC_WEBSITE_ID]], 
                      {'fields': ['name', 'domain', 'logo', 'favicon', 'social_facebook', 'social_instagram', 'social_twitter', 'social_youtube', 'social_linkedin', 'homepage_url']})
        if not src_web:
            log.warning("  Could not find source website configuration.")
            return
        src_web = src_web[0]
        
        vals = {}
        for k in ['name', 'domain', 'logo', 'favicon', 'social_facebook', 'social_instagram', 'social_twitter', 'social_youtube', 'social_linkedin', 'homepage_url']:
            if src_web.get(k):
                vals[k] = src_web[k]
                
        dst('website', 'write', [[DST_WEBSITE_ID], vals])
        log.info(f"  Updated website configuration for '{vals.get('name')}'")
    except Exception as e:
        log.error(f"  Failed to update website config: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Step 4b – Migrate Custom Views (Headers, Footers, Snippets)
# ──────────────────────────────────────────────────────────────────────────────

def migrate_custom_views(src, dst, id_map):
    log.info("  Fetching custom views (Headers, Footers, Themes) ...")
    try:
        custom_views = src('ir.ui.view', 'search_read',
                           [[('website_id', '=', SRC_WEBSITE_ID), ('type', '=', 'qweb')]],
                           {'fields': ['id', 'name', 'key', 'arch_db']})
        
        log.info(f"  Found {len(custom_views)} custom website views.")
        
        for view in custom_views:
            if not view.get('key'):
                continue
                
            new_arch = rewrite_html(view.get('arch_db', ''), id_map)
            if not new_arch:
                continue
                
            existing = dst('ir.ui.view', 'search_read', 
                           [[('key', '=', view['key']), '|', ('website_id', '=', DST_WEBSITE_ID), ('website_id', '=', False)]],
                           {'fields': ['id', 'website_id']})
            
            if existing:
                target_view = existing[0]
                for ex in existing:
                    if ex.get('website_id') and ex['website_id'][0] == DST_WEBSITE_ID:
                        target_view = ex
                        break
                dst('ir.ui.view', 'write', [[target_view['id']], {'arch_db': new_arch}])
                log.info(f"    Updated custom view: {view['key']}")
                
    except Exception as e:
        log.error(f"  Failed to update custom views: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Step 4c – Migrate pages and views
# ──────────────────────────────────────────────────────────────────────────────

def migrate_pages(src, dst, id_map):
    log.info("  Fetching pages from v18 ...")
    pages = src('website.page', 'search_read',
                [[]],
                {'fields': ['id', 'name', 'url', 'view_id', 'is_published',
                            'website_indexed', 'date_publish']})
    log.info(f"  Found {len(pages)} pages.")

    # Index existing pages in dst by URL
    dst_pages  = dst('website.page', 'search_read', [[]], {'fields': ['id', 'url', 'view_id']})
    dst_by_url = {p['url']: p for p in dst_pages}

    for page in pages:
        url         = page['url']
        name        = page['name']
        view_id_src = page['view_id'][0] if page.get('view_id') else None
        if not view_id_src:
            log.warning(f"  Page '{url}' has no view_id — skipped.")
            continue

        src_view = src('ir.ui.view', 'read', [[view_id_src]], {'fields': ['name', 'arch_db', 'key']})
        if not src_view:
            log.warning(f"  View {view_id_src} missing — skipped.")
            continue
        src_view = src_view[0]

        new_arch = rewrite_html(src_view['arch_db'], id_map)

        existing = dst_by_url.get(url)
        if existing:
            dst_view_id = existing['view_id'][0] if existing.get('view_id') else None
            if dst_view_id:
                try:
                    dst('ir.ui.view', 'write', [[dst_view_id], {'arch_db': new_arch}])
                    log.info(f"  Updated  '{url}'")
                except Exception as e:
                    log.error(f"  Update FAILED '{url}': {e}")
            else:
                log.warning(f"  Page '{url}' exists in v19 but has no view_id.")
        else:
            try:
                view_key = (src_view.get('key') or
                            f"website.imported_{url.strip('/').replace('/', '_') or 'home'}")
                # Avoid key collision
                if dst('ir.ui.view', 'search', [[('key', '=', view_key)]]):
                    view_key += '_v18'

                new_view_id = dst('ir.ui.view', 'create', [{
                    'name':    src_view['name'],
                    'type':    'qweb',
                    'arch_db': new_arch,
                    'key':     view_key,
                }])
                page_vals = {
                    'url':             url,
                    'name':            name,
                    'view_id':         new_view_id,
                    'is_published':    page.get('is_published', True),
                    'website_indexed': page.get('website_indexed', True),
                }
                if page.get('date_publish'):
                    page_vals['date_publish'] = page['date_publish']
                dst('website.page', 'create', [page_vals])
                log.info(f"  Created  '{url}'")
            except Exception as e:
                log.error(f"  Create FAILED '{url}': {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Step 5 – Migrate menus
# ──────────────────────────────────────────────────────────────────────────────

def migrate_menus(src, dst):
    src_menus = src('website.menu', 'search_read',
                    [[]],
                    {'fields': ['id', 'name', 'url', 'parent_id', 'sequence',
                                'is_visible', 'page_id']})
    log.info(f"  Found {len(src_menus)} menus in v18.")

    # Map URL → dst page id
    dst_pages        = dst('website.page', 'search_read', [[]], {'fields': ['id', 'url']})
    dst_page_by_url  = {p['url']: p['id'] for p in dst_pages}

    # Clear existing non-root menus in v19
    to_delete = dst('website.menu', 'search', [[('parent_id', '!=', False)]])
    if to_delete:
        try:
            dst('website.menu', 'unlink', [to_delete])
            log.info(f"  Cleared {len(to_delete)} old menus in v19.")
        except Exception as e:
            log.warning(f"  Could not clear old menus: {e}")

    # Destination root menu
    dst_roots   = dst('website.menu', 'search_read',
                      [[('parent_id', '=', False)]],
                      {'fields': ['id']})
    dst_root_id = dst_roots[0]['id'] if dst_roots else None

    src_roots = [m for m in src_menus if not m.get('parent_id')]
    menu_map  = {m['id']: dst_root_id for m in src_roots if dst_root_id}

    def build_tree(parent_src, parent_dst):
        children = sorted(
            [m for m in src_menus if m.get('parent_id') and m['parent_id'][0] == parent_src],
            key=lambda x: x.get('sequence') or 0
        )
        for m in children:
            page_dst = None
            if m.get('page_id'):
                info = src('website.page', 'read', [[m['page_id'][0]]], {'fields': ['url']})
                if info:
                    page_dst = dst_page_by_url.get(info[0]['url'])
            vals = {
                'name':       m['name'],
                'url':        m.get('url') or '/',
                'sequence':   m.get('sequence') or 10,
                'is_visible': m.get('is_visible', True),
                'parent_id':  parent_dst,
            }
            if page_dst:
                vals['page_id'] = page_dst
            try:
                new_id = dst('website.menu', 'create', [vals])
                menu_map[m['id']] = new_id
                log.info(f"    Menu '{m['name']}' → [{new_id}]")
                build_tree(m['id'], new_id)
            except Exception as e:
                log.error(f"    Menu '{m['name']}' FAILED: {e}")

    for sr in src_roots:
        build_tree(sr['id'], dst_root_id)

    log.info("  Menu migration done.")


# ──────────────────────────────────────────────────────────────────────────────
# Step 6 – Migrate custom CSS/JS snippets
# ──────────────────────────────────────────────────────────────────────────────

def migrate_custom_assets(src, dst):
    css_js = src('ir.attachment', 'search_read',
                 [[('name', '=like', 'custom.%.css'),
                   ('res_model', '=', 'website')]],
                 {'fields': ['id', 'name', 'datas', 'public', 'res_model', 'res_id']})
    log.info(f"  Found {len(css_js)} custom CSS/JS assets.")
    for att in css_js:
        if not att.get('datas'):
            continue
        existing = dst('ir.attachment', 'search',
                       [[('name', '=', att['name']), ('res_model', '=', 'website')]])
        vals = {'name': att['name'], 'datas': att['datas'],
                'public': True, 'res_model': 'website'}
        if existing:
            dst('ir.attachment', 'write', [existing, vals])
            log.info(f"    Updated: {att['name']}")
        else:
            dst('ir.attachment', 'create', [vals])
            log.info(f"    Created: {att['name']}")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 62)
    log.info("   Odoo Website Migration  v18 → v19")
    log.info("=" * 62)

    try:
        log.info("\nConnecting ...")
        src = connect(SRC_URL, SRC_DB, SRC_USER, SRC_PASS)
        dst = connect(DST_URL, DST_DB, DST_USER, DST_PASS)

        if not src or not dst:
            log.error("Failed to connect to source or destination. Exiting.")
            sys.exit(1)

        # ── 1. Find every attachment ID used anywhere in v18 HTML
        log.info("\n[Step 1] Scanning HTML for referenced attachment IDs ...")
        required_ids = collect_referenced_attachment_ids(src)

        # ── 2. Migrate images, build {old_id → new_id} map
        log.info("\n[Step 2] Migrating images ...")
        id_map = migrate_images(src, dst, required_ids)

        # Verify all required IDs were mapped
        missing = required_ids - set(id_map.keys())
        if missing:
            log.warning(f"  WARNING: {len(missing)} referenced IDs could not be mapped: {missing}")
        else:
            log.info(f"  All {len(required_ids)} referenced image IDs successfully mapped ✓")

        # ── 3. Migrate custom CSS/JS assets
        log.info("\n[Step 3] Migrating custom CSS/JS assets ...")
        migrate_custom_assets(src, dst)

        # ── 4a. Migrate website configuration
        log.info("\n[Step 4a] Migrating Website Configuration ...")
        migrate_website_config(src, dst)

        # ── 4b. Migrate custom global views (Headers, Footers)
        log.info("\n[Step 4b] Migrating Custom Views (Headers, Footers) ...")
        migrate_custom_views(src, dst, id_map)

        # ── 4c. Migrate pages with HTML rewriting
        log.info("\n[Step 4c] Migrating pages & views (with image ID rewriting) ...")
        migrate_pages(src, dst, id_map)

        # ── 5. Migrate menus
        log.info("\n[Step 5] Migrating menus ...")
        migrate_menus(src, dst)

        log.info("\n" + "=" * 62)
        log.info("   MIGRATION COMPLETE!")
        log.info("   Reload http://localhost:9090 to verify the result.")
        log.info("=" * 62)
    except Exception as e:
        log.error(f"An unexpected fatal error occurred during migration: {e}")
        log.info("Script exited safely without traceback.")


if __name__ == '__main__':
    main()
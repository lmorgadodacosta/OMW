#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, sqlite3
from flask import Flask, current_app, g
from collections import defaultdict as dd

from common_sql import *
from omw_sql import *

app = Flask(__name__)
with app.app_context():

    def lang_select_options(selected_lang_id):

        html = ''
        lang_id, lang_code = fetch_langs()
        for lid in lang_id.keys():
            if int(selected_lang_id) == int(lid):
                html += """<option value="{}" selected>{}</option>
                    """.format(lid, lang_id[lid][1])
            else:
                html += """<option value="{}">{}</option>
                    """.format(lid, lang_id[lid][1])
        return html


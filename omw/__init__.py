#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, sqlite3, datetime, urllib, gzip, requests
from time import sleep
from flask import Flask, render_template, g, request, redirect, url_for, send_from_directory, session, flash, jsonify, make_response, Markup
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user, wraps
from itsdangerous import URLSafeTimedSerializer # for safe session cookies
from collections import defaultdict as dd
from hashlib import md5
from werkzeug import secure_filename
from lxml import etree

from common_login import *
from common_sql import *
from omw_sql import *
import omw_html 
from wn_syntax import *

from math import log

app = Flask(__name__)
app.secret_key = "!$flhgSgngNO%$#SOET!$!"
app.config["REMEMBER_COOKIE_DURATION"] = datetime.timedelta(minutes=30)


################################################################################
# LOGIN
################################################################################
login_manager.init_app(app)

@app.route("/login", methods=["GET", "POST"])
def login():
    """ This login function checks if the username & password
    match the admin.db; if the authentication is successful,
    it passes the id of the user into login_user() """

    if request.method == "POST" and \
       "username" in request.form and \
       "password" in request.form:
        username = request.form["username"]
        password = request.form["password"]

        user = User.get(username)

        # If we found a user based on username then compare that the submitted
        # password matches the password in the database. The password is stored
        # is a slated hash format, so you must hash the password before comparing it.
        if user and hash_pass(password) == user.password:
            login_user(user, remember=True)
            # FIXME! Get this to work properly...
            # return redirect(request.args.get("next") or url_for("index"))
            return redirect(url_for("index"))
        else:
            flash(u"Invalid username, please try again.")
    return render_template("login.html")

@app.route("/logout")
@login_required(role=0, group='open')
def logout():
    logout_user()
    return redirect(url_for("index"))
################################################################################



################################################################################
# SET UP CONNECTION WITH DATABASES
################################################################################
@app.before_request
def before_request():
    g.admin = connect_admin()
    g.omw = connect_omw()

@app.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        g.admin.close()
        g.omw.close()
################################################################################


################################################################################
# AJAX REQUESTS
################################################################################
@app.route('/_thumb_up_id')
def thumb_up_id():
    user = fetch_id_from_userid(current_user.id)
    ili_id = request.args.get('ili_id', None)
    rate = 1
    r = rate_ili_id(ili_id, rate, user)

    counts, up_who, down_who = f_rate_summary([ili_id])
    html = """ <span style="color:green" title="{}">+{}</span><br>
               <span style="color:red"  title="{}">-{}</span>
           """.format(up_who[int(ili_id)], counts[int(ili_id)]['up'],
                      down_who[int(ili_id)], counts[int(ili_id)]['down'])
    return jsonify(result=html)


@app.route('/_thumb_down_id')
def thumb_down_id():
    user = fetch_id_from_userid(current_user.id)
    ili_id = request.args.get('ili_id', None)
    rate = -1
    r = rate_ili_id(ili_id, rate, user)

    counts, up_who, down_who = f_rate_summary([ili_id])
    html = """ <span style="color:green" title="{}">+{}</span><br>
               <span style="color:red"  title="{}">-{}</span>
           """.format(up_who[int(ili_id)], counts[int(ili_id)]['up'],
                      down_who[int(ili_id)], counts[int(ili_id)]['down'])
    return jsonify(result=html)


@app.route('/_comment_id')
def comment_id():
    user = fetch_id_from_userid(current_user.id)
    ili_id = request.args.get('ili_id', None)
    comment = request.args.get('comment', None)
    comment = str(Markup.escape(comment))
    dbinsert = comment_ili_id(ili_id, comment, user)
    return jsonify(result=dbinsert)


@app.route('/_detailed_id')
def detailed_id():
    ili_id = request.args.get('ili_id', None)
    rate_hist = fetch_rate_id([ili_id])
    comm_hist = fetch_comment_id([ili_id])
    users = fetch_allusers()

    r_html = ""
    for r, u, t in rate_hist[int(ili_id)]:
        r_html += '{} ({}): {} <br>'.format(users[u]['userID'], t, r)

    c_html = ""
    for c, u, t in comm_hist[int(ili_id)]:
        c_html += '{} ({}): {} <br>'.format(users[u]['userID'], t, c)

    html = """
    <td colspan="9">
    <div style="width: 49%; float:left;">
    <h6>Ratings</h6>
    {}</div>
    <div style="width: 49%; float:right;">
    <h6>Comments</h6>
    {}</div>
    </td>""".format(r_html, c_html)

    return jsonify(result=html)


@app.route('/_confirm_wn_upload')
def confirm_wn_upload_id():
    user = fetch_id_from_userid(current_user.id)
    fn = request.args.get('fn', None)
    upload = confirmUpload(fn, user)
    return jsonify(result=upload)


@app.route('/_add_new_project')
def add_new_project():
    user = fetch_id_from_userid(current_user.id)
    proj = request.args.get('proj_code', None)
    proj = str(Markup.escape(proj))
    if user and proj:
        dbinsert = insert_new_project(proj, user)
        return jsonify(result=dbinsert)
    else:
        return jsonify(result=False)


@app.route("/_load_lang_selector",methods=["GET"])
def omw_lang_selector():
    selected_lang = request.cookies.get('selected_lang')
    selected_lang2 = request.cookies.get('selected_lang2')
    lang_id, lang_code = fetch_langs()

    # The options in the main_lang_selector are being used
    # to populate language selectors in the edit interfaces,
    # which is also is setting the default language
    html = """<select id="main_lang_selector" name="lang" 
               style="font-size: 85%; width: 9em" required>"""
    html += omw_html.lang_select_options(selected_lang)
    html += '</select>'

    html += """<select id="backoff_lang_selector" name="lang2" 
                style="font-size: 85%; width: 9em" required>"""
    html += omw_html.lang_select_options(selected_lang2)
    html += '</select>'

    return jsonify(result=html)

@app.route('/_add_new_language')
def add_new_language():
    user = fetch_id_from_userid(current_user.id)
    bcp = request.args.get('bcp', None)
    bcp = str(Markup.escape(bcp))
    iso = request.args.get('iso', None)
    iso = str(Markup.escape(iso))
    name = request.args.get('name', None)
    name = str(Markup.escape(name))
    if bcp and name:
        dbinsert = insert_new_language(bcp, iso, name, user)
        return jsonify(result=dbinsert)
    else:
        return jsonify(result=False)


@app.route('/_add_new_definition')
def add_new_definition():
    user = fetch_id_from_userid(current_user.id)
    defi = request.args.get('def', None)
    defi = str(Markup.escape(defi))
    lang = request.args.get('lang', None)
    lang = str(Markup.escape(lang))
    if user and defi and lang:
        # dbinsert = insert_new_language(bcp, iso, name, user)
        # return jsonify(result=dbinsert)
        return jsonify(result=True)
    else:
        return jsonify(result=False)

@app.route('/_edit_definition')
def edit_definition():
    user = fetch_id_from_userid(current_user.id)
    defi = request.args.get('def', None)
    defi = str(Markup.escape(defi))
    if user and defi and lang:
        # dbinsert = insert_new_language(bcp, iso, name, user)
        # return jsonify(result=dbinsert)
        return jsonify(result=True)
    else:
        return jsonify(result=False)


@app.route('/_load_proj_details')
def load_proj_details():
    proj_id = request.args.get('proj', 0)
    if proj_id:
        proj_id = int(proj_id)
    else:
        proj_id = None

    projs = fetch_proj()
    srcs = fetch_src()
    srcs_meta = fetch_src_meta()

    html = str()

    if proj_id:
        i = 0
        for src_id in srcs.keys():

            if srcs[src_id][0] == projs[proj_id]:
                i += 1
                html += "<br><p><b>Source {}: {}-{}</b></p>".format(i,
                        projs[proj_id],srcs[src_id][1])

                for attr, val in srcs_meta[src_id].items():
                    html += "<p style='margin-left: 40px'>"
                    html += attr + ": " + val
                    html += "</p>"

    return jsonify(result=html)



@app.route('/_load_min_omw_concept/<ss>')
@app.route('/_load_min_omw_concept_ili/<ili_id>')
def min_omw_concepts(ss=None, ili_id=None):

    if ili_id:
        ss_ids = f_ss_id_by_ili_id(ili_id)
    else:
        ss_ids = [ss]

    pos = fetch_pos()
    langs_id, langs_code = fetch_langs()
    ss, senses, defs, exes, links = fetch_ss_basic(ss_ids)
    ssrels = fetch_ssrel()

    return jsonify(result=render_template('min_omw_concept.html',
                           pos = pos,
                           langs = langs_id,
                           senses=senses,
                           ss=ss,
                           links=links,
                           ssrels=ssrels,
                           defs=defs,
                           exes=exes))

@app.route('/_load_min_omw_sense/<sID>')
def min_omw_sense(sID=None):
    langs_id, langs_code = fetch_langs()
    pos = fetch_pos()
    sense =  fetch_sense(sID)
    forms=fetch_forms(sense[3])
    selected_lang = request.cookies.get('selected_lang')
    labels= fetch_labels(selected_lang,[sense[4]])
    src_meta= fetch_src_meta()
    src_sid=fetch_src_for_s_id([sID])
    #    return jsonify(result=render_template('omw_sense.html',
    return jsonify(result=render_template('min_omw_sense.html',
                                          s_id = sID,
                                          sense = sense,
                                          forms=forms,
                                          langs = langs_id,
                                          pos = pos,
                                          labels = labels,
                                          src_sid = src_sid,
                                          src_meta = src_meta))


# l=lambda:dd(l)
# vr = l()  # wn-lmf validation report

# @app.route('/_report_val1')
# def report_val1():
#     filename = request.args.get('fn', None)
#     if filename:
#         vr1 = val1_DTD(current_user, filename)
#         vr.update(vr1)
#         if vr1['dtd_val'] == True:
#             html = "DTD PASSED"
#             return jsonify(result=html)
#         else:
#             html = "DTD FAILED" + '<br>' + vr['dtd_val_errors']
#             return jsonify(result=html)
#     else:
#         return jsonify(result="ERROR")

@app.route('/_report_val2', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def report_val2():

    filename = request.args.get('fn', None)
    vr, filename, wn, wn_dtls = validateFile(current_user.id, filename)

    return jsonify(result=render_template('validation-report.html',
                    vr=vr, wn=wn, wn_dtls=wn_dtls, filename=filename))


    # validateFile()
    # filename = request.args.get('fn', None)
    # if filename:
    #     vr = val1_DTD(current_user, filename)
    #     if vr['dtd_val'] == True:
    #         html = "DTD PASSED"
    #         return jsonify(result=html)
    #     else:
    #         html = "DTD FAILED" + '<br>' + vr['dtd_val_errors']
    #         return jsonify(result=html)
    # else:
    #     return jsonify(result="ERROR")
    # return jsonify(result="TEST_VAL2")



@app.route('/_edit_examples')
def edit_examples():
    """
    This changes the examples div on a concept view.
    It shows to an authorised user: a form allowing them to edit, 
    add and delete examples.
    """

    # projs = fetch_proj_code()
    srcs = fetch_src()
    lang_id, lang_code = fetch_langs()


    # FIND ALL SOURCES THAT ARE LINKED TO THIS PROJECT
    edit_src_ids = []
    proj_code = request.args.get('proj', 0)
    if proj_code:
        # proj_id = int(projs[proj_code])
        for s in srcs:
            if srcs[s][0] == proj_code:
                edit_src_ids.append(s)
    else:
        proj_id = None

    ss_id = request.args.get('ss', 0)
    if ss_id:
        ss_id = int(ss_id)
    else:
        ss_id = None

    ssexes = fetch_ssexe_src_by_ssid(ss_id)


    # projs = fetch_proj()
    # srcs = fetch_src()
    # srcs_meta = fetch_src_meta()

    html = str()

    # html += str(ss_id)  #TEST
    # html += "<br>"  #TEST
    # html += str(ssexes)  #TEST


    # html += "<br>"
    # html += "<br>"
    # html += "<br>"

    for ssexe_id in ssexes['src']:
        (src_id, conf, t_src, u_src) =  ssexes['src'][ssexe_id]

        # html += str(src_id)  #TEST
        # html += "<br>"  #TEST
        # html += str(edit_src_ids)  #TEST
        if src_id in edit_src_ids:
            
            (ss, lang, exe_text, t, u) = ssexes['id'][ssexe_id]

            # html += "<br>"  #TEST
            # html += str(ssexes['id'][ssexe_id])  #TEST


            html += "<br>"
            html += """<input type="hidden" name="ss_id[]" value="{}">
                    """.format(ss_id)

            html += """<input type="hidden" name="ssexe_id[]" value="{}">
                    """.format(ssexe_id)

            html += """<input type="hidden" name="ssex_src_id[]" value="{}">
                    """.format(src_id)

            html += """<input type="text" name="ssex_text[]" value="{}" required>
                    """.format(exe_text)

            # Lang
            html += """<span id="lang_selection_span">"""
            html += """<select name="ssex_lang[]" 
                       style="font-size: 100%; width: 9em" required>"""
            html += omw_html.lang_select_options(lang)
            html += """</select>"""
            html += """</span>"""

            html += """ <i class="fa fa-trash-o" aria-hidden="true"></i> """
            html += """<span title="{}"><i class="fa fa-info-circle" 
            aria-hidden="true"></i></span>""".format(str(u)+', '+str(t))

    html += """<br><br>"""

    html += """<button id="add_new_example" name="add_new_example" 
    type="button"><i class="fa fa-plus-circle" aria-hidden="true"></i>
    Add New Example</button> """

    html += """<button type="button" class="medium green">Save Changes</button>
    <button type="button" class="medium red" 
    onClick="window.location.reload()">Discard Changes</button>"""

    html += """<script src="{}"></script>
    """.format(url_for('static', filename='js/omw.js'))
    return jsonify(result=html)


@app.route('/_add_new_example')
def add_new_example():
    user = fetch_id_from_userid(current_user.id)
    proj = request.args.get('proj', None)
    proj = str(Markup.escape(proj))
    proj_id = f_proj_id_by_code(proj)  # Get integer ID
    ss = request.args.get('ss', None)
    ss = int(ss)
    txt = request.args.get('txt', None)
    txt = str(Markup.escape(txt))
    lang = request.args.get('lang', None)
    lang = int(lang)

    src_id = f_src_id_by_proj_id_ver(proj_id, 'edit')
    sys.stderr.write(str(src_id))

    if not src_id:
        new_src_id = insert_src(proj_id, 'edit', user) 
        src_id = new_src_id[0]

    # Need to get a srcID
    if user and proj and ss and txt and lang:
        new_ssexe_id = insert_omw_ssexe(ss, lang, txt, user)
        new_ssexe_src_meta = insert_omw_ssexe_src(new_ssexe_id, src_id, 1, user)




        # dbinsert = insert_new_language(bcp, iso, name, user)
        # return jsonify(result=dbinsert)


        # def insert_omw_ssexe(ss_id, lang_id, e, u):
        #     return write_omw("""INSERT INTO ssexe (ss_id, lang_id, ssexe, u)
        #                     VALUES (?,?,?,?)""",
        #                  [ss_id, lang_id, e, u])
        # def insert_omw_ssexe_src(ssexe_id, src_id, conf, u):
        #     return write_omw("""INSERT INTO ssexe_src (ssexe_id, src_id, conf, u)
        #                     VALUES (?,?,?,?)""",
        #                  [ssexe_id, src_id, conf, u])



        return jsonify(result=True)
    else:
        return jsonify(result=False)


################################################################################


################################################################################
# VIEWS
################################################################################
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/ili', methods=['GET', 'POST'])
def ili_welcome(name=None):
    return render_template('ili_welcome.html')

@app.route('/omw', methods=['GET', 'POST'])
def omw_welcome(name=None):
    return render_template('omw_welcome.html')


@app.route("/useradmin",methods=["GET"])
@login_required(role=99, group='admin')
def useradmin():
    users = fetch_allusers()
    return render_template("useradmin.html", users=users)

@app.route("/langadmin",methods=["GET"])
@login_required(role=99, group='admin')
def langadmin():
    lang_id, lang_code = fetch_langs()
    return render_template("langadmin.html", langs=lang_id)

@app.route("/projectadmin",methods=["GET"])
@login_required(role=99, group='admin')
def projectadmin():
    projs = fetch_proj()
    return render_template("projectadmin.html", projs=projs)

@app.route('/allconcepts', methods=['GET', 'POST'])
def allconcepts():
    ili, ili_defs = fetch_ili()
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)

@app.route('/temporary', methods=['GET', 'POST'])
def temporary():
    ili = fetch_ili_status(2)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/deprecated', methods=['GET', 'POST'])
def deprecated():
    ili = fetch_ili_status(0)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/ili/concepts/<c>', methods=['GET', 'POST'])
def concepts_ili(c=None):
    c = c.split(',')
    ili, ili_defs = fetch_ili(c)
    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))

    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/ili/search', methods=['GET', 'POST'])
@app.route('/ili/search/<q>', methods=['GET', 'POST'])
def search_ili(q=None):

    if q:
        query = q
    else:
        query = request.form['query']

    src_id = fetch_src()
    kind_id = fetch_kind()
    status_id = fetch_status()

    ili = dict()
    for c in query_omw("""SELECT * FROM ili WHERE def GLOB ?
                         """, [query]):
        ili[c['id']] = (kind_id[c['kind_id']], c['def'],
                        src_id[c['origin_src_id']], c['src_key'],
                        status_id[c['status_id']], c['superseded_by_id'],
                             c['t'])


    rsumm, up_who, down_who = f_rate_summary(list(ili.keys()))
    return render_template('concept-list.html', ili=ili,
                           rsumm=rsumm, up_who=up_who, down_who=down_who)


@app.route('/upload', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def upload():
    return render_template('upload.html')

@app.route('/metadata', methods=['GET', 'POST'])
def metadata():
    return render_template('metadata.html')

@app.route('/join', methods=['GET', 'POST'])
def join():
    return render_template('join.html')


@app.route('/ili/validation-report', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def validationReport():

    vr, filename, wn, wn_dtls = validateFile(current_user.id)

    return render_template('validation-report.html',
                           vr=vr, wn=wn, wn_dtls=wn_dtls,
                           filename=filename)

@app.route('/ili/report', methods=['GET', 'POST'])
@login_required(role=0, group='open')
def report():
    passed, filename = uploadFile(current_user.id)
    return render_template('report.html',
                           passed=passed,
                           filename=filename)
    # return render_template('report.html')



@app.route('/omw/search', methods=['GET', 'POST'])
@app.route('/omw/search/<lang>,<lang2>/<q>', methods=['GET', 'POST'])
def search_omw(lang=None, q=None):

    if lang and q:
        lang_id = lang
        lang_id2 = lang2
        query = q
    else:
        lang_id = request.form['lang']
        lang_id2 = request.form['lang2']
        query = request.form['query']
    sense = dd(list)
    lang_sense = dd(lambda: dd(list))

    # GO FROM FORM TO SENSE
    for s in query_omw("""
        SELECT s.id as s_id, ss_id,  wid, fid, lang_id, pos_id, lemma
        FROM (SELECT w_id as wid, form.id as fid, lang_id, pos_id, lemma
              FROM (SELECT id, lang_id, pos_id, lemma
                    FROM f WHERE lemma GLOB ? AND lang_id in (?,?)) as form
              JOIN wf_link ON form.id = wf_link.f_id) word
        JOIN s ON wid=w_id
        """, [query,lang_id,lang_id2]):


        sense[s['ss_id']] = [s['s_id'], s['wid'], s['fid'],
                             s['lang_id'], s['pos_id'], s['lemma']]


        lang_sense[s['lang_id']][s['ss_id']] = [s['s_id'], s['wid'], s['fid'],
                                                s['pos_id'], s['lemma']]


    pos = fetch_pos()
    lang_dct, lang_code = fetch_langs()
    ss, senses, defs, exes, links = fetch_ss_basic(sense.keys())

    labels = fetch_labels(lang_id, set(senses.keys()))


    resp = make_response(render_template('omw_results.html',
                                         langsel = int(lang_id),
                                         langsel2 = int(lang_id2),
                                         pos = pos,
                                         lang_dct = lang_dct,
                                         sense=sense,
                                         senses=senses,
                                         ss=ss,
                                         links=links,
                                         defs=defs,
                                         exes=exes,
                                         labels=labels))

    resp.set_cookie('selected_lang', lang_id)
    resp.set_cookie('selected_lang2', lang_id2)
    return resp


@app.route('/omw/concepts/<ssID>', methods=['GET', 'POST'])
@app.route('/omw/concepts/ili/<iliID>', methods=['GET', 'POST'])
def concepts_omw(ssID=None, iliID=None, src=None):

    if iliID:
        ss_ids = f_ss_id_by_ili_id(iliID)
        ili, ilidefs = fetch_ili([iliID])
    else:
        ss_ids = [ssID]
        ili, ili_defs = dict(), dict()
    pos = fetch_pos()
    langs_id, langs_code = fetch_langs()
    
    ss, senses, defs, exes, links = fetch_ss_basic(ss_ids)
    if (not iliID) and int(ssID) in ss:
        iliID = ss[int(ssID)][0]
        ili, ilidefs = fetch_ili([iliID])
        
    sss = list(ss.keys())
    for s in links:
        for l in links[s]:
            sss.extend(links[s][l])
    selected_lang = request.cookies.get('selected_lang')
    labels = fetch_labels(selected_lang, set(sss))

    ssrels = fetch_ssrel()

    ss_srcs=fetch_src_for_ss_id(ss_ids)
    src_meta=fetch_src_meta()

    if src:
        try:
            (proj, ver) = src.split('-')
            # src_id = f_src_id_by_proj_ver(proj, ver)
        except:
            proj = None
            ver = None
    else:
        proj = None
        ver = None


    return render_template('omw_concept.html',
                           ssID=ssID,
                           iliID=iliID,
                           pos = pos,
                           langs = langs_id,
                           senses=senses,
                           ss=ss,
                           links=links,
                           ssrels=ssrels,
                           defs=defs,
                           exes=exes,
                           ili=ili,
                           selected_lang = selected_lang,
                           selected_lang2 = request.cookies.get('selected_lang2'),
                           labels=labels,
                           ss_srcs=ss_srcs,
                           src_meta=src_meta,
                           proj=proj,
                           ver=ver)


@app.route('/omw/senses/<sID>', methods=['GET', 'POST'])
def omw_sense(sID=None):
    langs_id, langs_code = fetch_langs()
    pos = fetch_pos()
    sense =  fetch_sense(sID)
    forms=fetch_forms(sense[3])
    selected_lang = request.cookies.get('selected_lang')
    labels= fetch_labels(selected_lang,[sense[4]])
    src_meta= fetch_src_meta()
    src_sid=fetch_src_for_s_id([sID])
    return render_template('omw_sense.html',
                           s_id = sID,
                           sense = sense,
                           forms=forms,
                           langs = langs_id,
                           pos = pos,
                           labels = labels,
                           src_sid = src_sid,
                           src_meta = src_meta)




# THIS SHOULD BE THE MAIN/SEARCH PAGE FOR EACH INDIVIDUAL PROJECT
@app.route('/omw/src/<src>', methods=['GET', 'POST'])
def src_omw(src=None):

    try:
        (proj, ver) = src.split('-')
        src_id = f_src_id_by_proj_ver(proj, ver)
    except:
        src_id = None

    # return concepts_omw(ss)
    return "FIXME. This should be an entry page for this project only! With search function, etc."


# URIs FOR ORIGINAL CONCEPT KEYS, BY INDIVIDUAL SOURCES
@app.route('/omw/src/<src>/<originalkey>', methods=['GET', 'POST'])
def src_omw_key(src=None, originalkey=None):

    try:
        (proj, ver) = src.split('-')
        src_id = f_src_id_by_proj_ver(proj, ver)
    except:
        src_id = None

    if src_id:
        try:
            ss = fetch_ss_id_by_src_orginalkey(src_id, originalkey)
        except:
            ss = None
    else:
        ss = None

    if src_id and ss:
        return concepts_omw(ss, src=src)
    else:
        return """This URI does not exist. <br>
        If you think it should exist, then please report this."""





## show wn statistics
##
## slightly brittle :-)
##
@app.route('/omw/wns/<w>', methods=['GET', 'POST'])
def omw_wn(w=None):
    if w:
        (proj, ver) = w.split('-')
        src_id = f_src_id_by_proj_ver(proj, ver)
        srcs_meta = fetch_src_meta()
        src_info = dd(str)
        for d in srcs_meta[src_id]:
            src_info[d['attr']]=d['val']

    return render_template('omw_wn.html',
                           wn = w,
                           src_id=src_id,
                           src_info=src_info,
                           src_stats=fetch_src_id_stats(src_id))

@app.context_processor
def utility_processor():
    def scale_freq(f, maxfreq=1000):
        if f > 0:
            return 100 + 100 * log(f)/log(maxfreq)
        else:
            return 100
    return dict(scale_freq=scale_freq)



## show proj statistics
#for proj in fetch_proj/


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

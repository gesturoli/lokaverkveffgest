from flask import Flask, render_template, url_for, request, flash, session, redirect
from flask_ckeditor import CKEditor
from datetime import datetime
import requests, json
from tinydb import TinyDB, Query
import random
import datetime

app = Flask(__name__)
ckeditor = CKEditor(app)
app.config['SECRET_KEY'] = '1234'  

ELDEN_RING_API = "https://eldenring.fanapis.com/api"
 
flokkar = ["weapons", "armors", "shields", "ashes", "talismans", 
            "incantations", "sorceries", "items", "materials", "spirits", 
            "ammos", "classes", "npcs", "bosses", "creatures", "locations"]

blogs = []


@app.route("/")
def index():
    genre = random.choice(flokkar)

    # 1. sækja metadata til að finna fjölda hluta
    meta_response = requests.get(f"{ELDEN_RING_API}/{genre}?limit=1&page=0")
    meta = meta_response.json()
    
    total_items = meta.get("total", 1)
    pages = max(total_items // 50, 0)

    # 2. velja gilda síðu
    page = random.randint(0, pages)

    # 3. sækja actual hluti
    response = requests.get(f"{ELDEN_RING_API}/{genre}?limit=50&page={page}")
    data = response.json()
    all_items = data.get("data", [])

    # 4. velja 30 random hluti úr þeim sem sækja má
    random_items = random.sample(all_items, min(len(all_items), 30))

    return render_template("index.html", items=random_items, genre=genre)



        
    

@app.route("/logout")
def logout():
    session.pop('admin', None)
    flash("Þú hefur verið skráður út.")
    return redirect(url_for('index'))    

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        e = request.form.get("email")
        p = request.form.get("password")

        if e == "admin@admin.is" and p == "123456":
            session['admin'] = True
            flash("Innskráning tókst")
            return redirect(url_for('admin'))
        else:
            flash("Rangt netfang eða lykilorð")

    return render_template("login.html")

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get('admin'):
        flash("Aðgangur Hafnaður")
        return redirect(url_for('login'))
        
    if request.method == "POST":
        title = request.form.get('titill')
        genre = request.form.get('genre')
        cKa= request.form.get('ckA')
        author = "admin@admin.is"
        date = datetime.datetime.today()
        if title and genre and cKa:
            post = {
                "author": author,
                "title": title,
                "genre": genre,
                "content": cKa,
                "date": date
                }
            blogs.append(post)
            flash("Blogg bætt við")
            return redirect(url_for('blogg'))
            
        else:
            flash("Vantar titil, flokkur eða innihald")
            return redirect(url_for('admin'))

    return render_template("admin.html", user=session.get('admin'))
        

@app.route("/info")
def info():
    genre = request.args.get("genre")
    page = request.args.get("page", default=0, type=int)

    if not genre:
        return render_template("info.html", items=None, genre=None, page=page)

    response = requests.get(f"{ELDEN_RING_API}/{genre}?limit=20&page={page}")
    data = response.json()

    items = data.get("data", [])

    return render_template("info.html", items=items, genre=genre, page=page)


@app.route("/blogg")
def blogg():    
    sorted_blogs = sorted(blogs, key=lambda x: x['date'], reverse=True)
    return render_template("blogg.html", blogs = sorted_blogs)





@app.route("/item/<genre>/<item_id>")
def item_page(genre, item_id):

    # Try multiple pages (0–20 is safe)
    for page in range(0, 20):
        response = requests.get(f"{ELDEN_RING_API}/{genre}?limit=50&page={page}")

        if response.status_code != 200:
            continue

        data = response.json()
        items = data.get("data", [])

        # SEARCH ALL ITEMS ON THIS PAGE
        for itm in items:
            if str(itm.get("id")) == str(item_id):
                return render_template("item.html", item=itm)

    return "Item not found", 404


@app.route("/search")
def search():
    query = request.args.get("q", "").lower().strip()

    if not query:
        return render_template("search.html", items=[], query=query)

    results = []
    seen_ids = set()  # forðast tvo eins

    # tékkar hvað passar
    SEARCH_FIELDS = ["name", "description", "category", "type", "location", "drops"]

    for genre in flokkar:
        # flettir þar til ekkert skilar sér
        for page in range(0, 30):

            try:
                resp = requests.get(f"{ELDEN_RING_API}/{genre}?limit=50&page={page}")

                # ef API skilar error, sleppa síðu
                try:
                    data = resp.json()
                except ValueError:
                    continue

                items = data.get("data", [])
                if not items:
                    break   # engar fleirri síður - stoppa flokk

                for itm in items:
                    # forðast duplicate
                    if itm.get("id") in seen_ids:
                        continue

                    # tékka "fields" hluti sem hlutirnir hafa
                    match = False
                    for field in SEARCH_FIELDS:
                        text = str(itm.get(field, "")).lower()
                        if query in text:
                            match = True
                            break

                    if match:
                        itm["genre"] = genre  # þarf til að opna hlut
                        results.append(itm)
                        seen_ids.add(itm["id"])

            except Exception:
                continue

    return render_template("search.html", items=results, query=query)


@app.route("/delete_blog/<int:blog_id>", methods=["POST"])
def delete_blog(blog_id):
    if not session.get('admin'):
        flash("Aðgangur Hafnaður")
        return redirect(url_for('login'))
    
    if 0 <= blog_id < len(blogs):
        blogs.pop(blog_id)
        flash("Blogg eytt")
    else:
        flash("Blogg fannst ekki")
    
    return redirect(url_for('blogg'))


@app.route("/edit_blog/<int:blog_id>", methods=["GET", "POST"])
def edit_blog(blog_id):
    if not session.get('admin'):
        flash("Aðgangur Hafnaður")
        return redirect(url_for('login'))
    
    if blog_id < 0 or blog_id >= len(blogs):
        flash("Blogg fannst ekki")
        return redirect(url_for('blogg'))
    
    blog = blogs[blog_id]
    
    if request.method == "POST":
        title = request.form.get('titill')
        genre = request.form.get('genre')
        content = request.form.get('ckA')
        
        if title and genre and content:
            blogs[blog_id] = {
                "author": blog['author'],
                "title": title,
                "genre": genre,
                "content": content,
                "date": blog['date']
            }
            flash("Blogg uppfært")
            return redirect(url_for('blogg'))
        else:
            flash("Vantar titil, flokkur eða innihald")
    
    return render_template("edit_blog.html", blog=blog, blog_id=blog_id)




    """
    genre = request.args.get("genre")
    page = random.randint(1, 15)
    if not genre:
        return render_template("info.html", items=None, genre=None)


    response = requests.get(f"{ELDEN_RING_API}/{genre}?limit=20&page={page}")
    data = response.json()

    items = data.get("data", [])
    

    return render_template("info.html", items=items, genre=genre)
    """

        

if __name__ == "__main__":
    app.run(debug=True)

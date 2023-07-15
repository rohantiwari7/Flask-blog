from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import json, os, math  #secrets,
from flask_mail import Mail
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
c = open('config.json', 'r')
params = json.load(c)['params']
app.secret_key = params['secret']     #  import secrets,  secrets.token_hex()

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['mail_username'],
    MAIL_PASSWORD=params['mail_password']
)
mail = Mail(app)

c = open('config.json', 'r')
social_media = json.load(c)['social_media']

local_server = params['local_server']
if local_server == "True":
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    print("prod server")
# initialize the app with the extension
db = SQLAlchemy(app)


class Contacts(db.Model):
    '''sno, name, email, phone, msg, date'''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(13), nullable=False)
    msg = db.Column(db.String, nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    '''sno, title, content, author, date, slug '''
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60), nullable=False)
    content = db.Column(db.String(600), nullable=False)
    author = db.Column(db.String(30), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    slug = db.Column(db.String(40), nullable=False)
    img_name = db.Column(db.String(35), nullable=True)


@app.route("/")
def home():
    posts = Posts.query.all()    #[-social_media["no_of_posts"]:][::-1]
    last = int(math.ceil(len(posts)/int(social_media["no_of_posts"])))
    page = request.args.get('page')
    if not page:
        page = 1
    else:
        page = int(page)
    #Only Page
    if last == 1:
        prev = '#'
        next = '#'
    #First page
    elif page == 1:
        prev = '#'
        next = '?page='+str(page+1)
    #last page
    elif page == last:
        prev = '?page='+str(page-1)
        next = '#'
    #mid page
    else:
        prev = '?page='+str(page-1)
        next = '?page='+str(page+1)

    posts = posts[::-1]
    posts = posts[(page-1)*int(social_media["no_of_posts"]):page*int(social_media["no_of_posts"])]
    return render_template('index.html', social_media=social_media, posts=posts, prev=prev, next=next)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'user' in session and session['user'] == params["admin_user"]:
        return redirect('/dashboard')
    if request.method == 'POST':
        #print('post')
        admin_user = request.form.get('aname')
        admin_pass = request.form.get('apass')
        #print(admin_user,'  ', admin_pass)
        if admin_user == params['admin_user'] and admin_pass == params['admin_pass']:  #admin_user and admin_pass and
            session['user'] = params['admin_user']
            return redirect('/dashboard')

    return render_template('login.html')


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params["admin_user"]:
        posts = Posts.query.all()
        return render_template('dashboard.html', social_media=social_media, posts=posts)
    return redirect('/login')


@app.route('/logout')
def logout():
    if 'user' in session:
        session.pop('user', None)
    return redirect('/login')


@app.route('/post/<string:post_slug>')
def post_route(post_slug):
    #sno, title, content, author, date, slug   ---   DB variables
    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template('post.html', social_media=social_media, post=post)


@app.route('/edit/<string:sno>', methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params["admin_user"]:
        if request.method == 'GET':
            if sno == '0':
                return render_template('add.html', social_media=social_media, sno=sno)
            else:
                post = Posts.query.filter_by(sno=sno).first()
                return render_template('edit.html', social_media=social_media, sno=sno, post=post)

        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            slug = request.form.get('slug')
            author = request.form.get('author')
            img_name = request.form.get('img_name')

            if sno == '0':
                post = Posts(title=title, content=content, slug=slug, author=author, img_name=img_name, date=datetime.now())
                db.session.add(post)
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.content = content
                post.author = author
                post.slug = slug
                post.img_name = img_name
                db.session.commit()
                return redirect(url_for('dashboard'))

    return redirect('/login')


@app.route('/delete/<string:sno>')
def delete(sno):
    if 'user' in session and session['user'] == params["admin_user"]:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and (filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS )


@app.route('/uploader', methods=['GET', 'POST'])
def uploader():
    if 'user' in session and session['user'] == params["admin_user"]:
        if request.method == 'POST':
            file = request.files['file1']
            if file.filename == '':
                flash('No selected file')
                return redirect('/dashboard')
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(params['upload_location'], filename))
                return f"Uploaded Successfully!  saved with filename =>  {filename}"  #, {"Refresh": "6,url=/dashboard"}

    return redirect('/dashboard')


@app.route('/about')
def about():
    return render_template('about.html', social_media=social_media)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')    #HTML
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, email=email, msg=message, phone=phone, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message(f'Message from {name}',
                          sender=email,
                          recipients=[params['mail_username']],
                          body=message+'\n'+phone+'\n'+email
                          )

    "'name,email,phone,message     HTML variables received'"
    '''sno, name, email, phone, msg, date      DB variables'''

    return render_template('contact.html', social_media=social_media)


if __name__ == '__main__':
    app.debug = True
    app.run()

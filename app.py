from flask import Flask, render_template, url_for, request, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from decimal import Decimal

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Jar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Numeric(38, 2), default=0)
    currency = db.Column(db.String, nullable=False)
    operations = db.relationship('Operation', backref='jar', cascade='all, delete-orphan')

    def __repr__(self):
        return 'Jar %r: %s %s' % (self.id, self.balance, self.currency)

    def charge(self, amount, title):
        self.transfer(amount * -1, title)

    def credit(self, amount, title):
        self.transfer(amount, title)

    def transfer(self, amount, title):
        """
        :param amount: decimal
        :param title: string
        """

        self.balance += amount
        operation = Operation(jar_id=self.id, value=amount, title=title)
        db.session.add(self)
        db.session.add(operation)
        db.session.commit()


class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)
    jar_id = db.Column(db.Integer, db.ForeignKey('jar.id'), nullable=False)
    value = db.Column(db.Numeric(38, 2))
    title = db.Column(db.String, nullable=False)

    def __repr__(self):
        return '<Operation %r>' % self.id

    @property
    def datetime_short(self):
        return self.datetime.replace(microsecond=0)


@app.route('/', methods=['POST', 'GET'])
def index():
    jars = Jar.query.all()

    if request.method == 'POST':
        jar_currency = request.form['currency']
        jar = Jar(currency=jar_currency)

        try:
            db.session.add(jar)
            db.session.commit()
            return redirect("/")
        except:
            return "There was an issue adding new jar."
    else:
        return render_template("index.html", jars=jars)


@app.route('/delete/<int:id>')
def delete(id):
    jar = Jar.query.get(id)

    try:
        db.session.delete(jar)
        db.session.commit()
    except:
        return "There was an issue deleting jar."

    return redirect("/")


@app.route('/jar/<int:id>', methods=['GET', 'POST'])
def jar(id):
    jar = Jar.query.get_or_404(id)

    return render_template("jar.html", jar=jar)


@app.route('/jar/add/<int:id>', methods=['GET', 'POST'])
def add(id):
    jar = Jar.query.get_or_404(id)

    if request.method == 'POST':
        amount = Decimal(request.form['amount'])
        title = request.form['title']
        try:
            jar.credit(amount, title)
            return redirect("/jar/%s" % id)
        except:
            return "There was an issue adding money to the jar."

    else:
        return render_template("add.html", jar=jar)


@app.route('/jar/withdraw/<int:id>', methods=['GET', 'POST'])
def withdraw(id):
    jar = Jar.query.get_or_404(id)
    if not jar.balance > 0:
        return "Not possible to withdraw from jar %s" % id

    if request.method == 'POST':
        amount = Decimal(request.form['amount'])
        title = request.form['title']
        try:
            jar.charge(amount, title)
            return redirect("/jar/%s" % id)
        except:
            return "There was an issue withdrawing money from the jar."

    else:
        return render_template("withdraw.html", jar=jar)


@app.route('/jar2jar', methods=['GET', 'POST'])
def jar2jar_transfer_select():
    jars = [jar for jar in Jar.query.all() if jar.balance > 0]

    if request.method == 'POST':
        id = request.form['id']
        return redirect('/jar2jar/%s' % id)

    if not jars:
        return "No money in any jar!"
    return render_template("jar2jar_select.html", jars=jars)


@app.route('/jar2jar/<int:id>', methods=['GET', 'POST'])
def jar2jar_transfer(id):
    jar_charged = Jar.query.get_or_404(id)
    valid_jars = [jar for jar in Jar.query.all() if jar.currency == jar_charged.currency and jar.id != jar_charged.id]

    if request.method == 'POST':
        amount = Decimal(request.form['amount'])
        jar_credited = Jar.query.get_or_404(request.form['jar_credited_id'])
        title = request.form['title']
        jar_charged.charge(amount, title)
        jar_credited.credit(amount, title)
        return redirect('/')

    return render_template("jar2jar.html", jar_charged=jar_charged, valid_jars=valid_jars)


@app.route('/operations', methods=['GET', 'POST'])
def operations():
    all_operations = Operation.query.all()
    jar_ids = list(set([operation.jar_id for operation in all_operations]))
    jars = [Jar.query.get_or_404(jar_id) for jar_id in jar_ids]

    if request.method == 'POST':
        id = int(request.form['id'])
        operations = Operation.query.filter_by(jar_id=id).all()
    else:
        id = None
        operations = all_operations

    return render_template("operations.html", operations=operations, jars=jars, id=id)


@app.route('/operations/<int:id>', methods=['GET', 'POST'])
def operations_single_jar(id):
    operations = Operation.query.filter_by(jar_id=id).all()
    jar_ids = list(set([operation.jar_id for operation in Operation.query.all()]))
    jars = [Jar.query.get_or_404(jar_id) for jar_id in jar_ids]

    return render_template("operations.html", operations=operations, jars=jars, id=id)


if __name__ == "__main__":
    app.run(debug=True)

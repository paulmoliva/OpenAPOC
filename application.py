import flask, json, simplejson
import dwollav2, dwollaswagger
import os
from flask_cors import CORS
import flask_login
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from sqlalchemy import and_, or_, func

application = flask.Flask(__name__)
CORS(application)

ACTIVE_CACHE = {}

application.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('CLEARDB_DATABASE_URL')
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
application.secret_key = os.getenv('SECRET_KEY') or 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

login_manager = flask_login.LoginManager()
login_manager.init_app(application)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@application.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = flask.request.form
    if form.get('username'):
        # Login and validate the user.
        # user should be an instance of your `User` class
        user = User.query.filter(User.name == form['username']).first()
        if bcrypt.checkpw(form.get('password').encode('utf-8'), user.password.encode('utf-8')):
            flask_login.login_user(user)
            return flask.redirect('/')
        else:
            return flask.render_template('login.html', form=form, error="Problem logging you in. Please try again.")
    return flask.render_template('login.html', form=form)


@application.route('/signup', methods=['GET', 'POST'])
def signup():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = flask.request.form
    if form.get('username'):
        # Login and validate the user.
        # user should be an instance of your `User` class
        user = User.query.filter(User.name == form['username']).first()
        if user:
            return flask.Response('User exists!', 401)
        else:
            user = User()
            user.name = form.get('username')
            salt = bcrypt.gensalt()
            user.password = bcrypt.hashpw(form.get('password').encode('utf-8'), salt)
            db.session.add(user)
            db.session.commit()
            flask_login.login_user(user)
            return flask.redirect(flask.url_for('index'))
    return flask.render_template('signup.html', form=form)


@application.route('/logout')
def logout():
    flask_login.logout_user()
    return flask.redirect('/login')



SCORE_QUERY = '''
update van as t
set t.donor_score = (
	select (sum(apoc.`total_amount`) * (case apoc.lean when 'r' then -1 when 'l' then 1 else 0 END))
	from apoc
	where apoc.`van_id` = t.`VANID`
);
'''

ADD_TO_SCORE_QUERY = '''
update van as t
set t.add_to_score =
    case t.donor_score < -1
        when true then -1
        else
            case t.donor_score > 1
                when true then 1 else 0
            end
    end
'''

DONORS_LEAN_QUERY ='''
update donors as t
set lean = (
    select leans from campaigns where campaigns.id = t.campaign_id
);
'''

LEANS_QUERY = '''
update campaigns as t
set leans =
    case ((select sum(con.add_to_score) from van con
    join apoc d on d.van_id = con.VANID
    where d.campaign_id = t.id
    ) < -1) when true then 'r' else case((select sum(con.add_to_score) from contributors con
    join apoc d on d.van_id = con.VANID
    where d.campaign_id = t.id
    ) > 1) when true then 'l' else null end end,

score =
    (select sum(con.add_to_score) from van con
    join apoc d on d.van_id = con.VANID
    where d.campaign_id = t.id
    );
'''

UPDATE_VOTES_QUERY = '''
update van as t set primary_votes =
    cast(t.`Primary98` as decimal) + cast(t.`Primary00` as decimal) + cast(t.`Primary02` as decimal) + cast(t.`Primary04` as decimal) + cast(t.`Primary06` as decimal) + cast(t.`Primary08` as decimal) + cast(t.`Primary10` as decimal) + cast(t.`Primary12` as decimal) + cast(t.`Primary14` as decimal) + cast(t.`Primary16` as decimal)
)
'''

TRAIN_ORDER = [DONORS_LEAN_QUERY, SCORE_QUERY, ADD_TO_SCORE_QUERY, LEANS_QUERY]

@application.route('/dwolla')
def dwolla():
    client = dwollav2.Client(
        key=os.environ['DWOLLA_APP_KEY'],
        secret=os.environ['DWOLLA_APP_SECRET'],
        environment='sandbox'
    )

    swag_client = dwollaswagger.ApiClient()

    #app_token = client.Auth.client()

    #account_token = client.Token(access_token=os.environ['DWOLLA_ACCESS_TOKEN'], refresh_token=os.environ['DWOLLA_ACCESS_TOKEN'])

    dwollaswagger.configuration.access_token = os.environ['DWOLLA_ACCESS_TOKEN']

    # For UAT/Sandbox
    client = dwollaswagger.ApiClient('https://api-uat.dwolla.com')

    customer_id = '3eef30d3-5829-499e-80af-0e60e8714e6e'

    customer_url = 'http://api.dwolla.com/customers/{0}'.format(customer_id)
    customers_api = dwollaswagger.CustomersApi(client)

    token = customers_api.create_funding_sources_token_for_customer(customer_url)

    return flask.render_template('bank.html', token=token.get('token'))


@application.route('/privacy')
def privacy():
    return flask.render_template('privacypolicy.htm')


@application.route('/')
def hello_world():
    if flask_login.current_user.is_authenticated:
        return flask.render_template(
            'index.html'
        )
    else:
        return flask.render_template(
            'landing.html'
        )


@application.route('/login')
def login_page():
    if flask_login.current_user.is_authenticated:
        return flask.render_template(
            'index.html'
        )
    else:
        return flask.render_template(
            'login.html'
        )


@application.route('/about')
def about_page():
    return flask.render_template(
        'about.html'
    )


# @application.route('/top')
# def top_donors():
#     per_page = 50
#     offset = int(flask.request.args.get('offset', 0))
#     contributors = Contributor.query.filter(Contributor.is_person).order_by(Contributor.score.desc()).limit(per_page).offset(offset).all()
#     return flask.render_template(
#         'top.html',
#         contributors=contributors,
#         offset=offset,
#         per_page=per_page
#     )



# @application.route('/campaigns')
# def all_campaigns():
#     all_campaigns = Campaign.query.filter(Campaign.leans == None).order_by(Campaign.name).all()
#     return flask.render_template(
#         'campaigns.html',
#         campaigns=all_campaigns
#     )


# @application.route('/campaigns', methods=['PUT'])
# def update_campaign():
#     the_json = flask.request.json
#     the_campaign = Campaign.query.filter(Campaign.name == the_json['name']).first()
#     the_campaign.leans = the_json['leans']
#     db.session.add(the_campaign)
#     db.session.commit()
#     db.engine.execute("UPDATE donors SET lean = '{lean}' WHERE Name = '{name}'".format(lean=the_json['leans'], name=the_json['name']))
#     return ''


# @application.route('/score_campaigns')
# def score_campaigns():
#     execute_queries(TRAIN_ORDER)
#     db.session.commit()
#     return 'done!'


# @application.route('/contributors/<int:contributor_id>')
# def show_contributor(contributor_id):
#     the_contributor = Contributor.query.get(contributor_id)
#     return flask.render_template(
#         'show_contributor.html',
#         contributor=the_contributor
#     )


# @application.route('/campaigns/<int:campaign_id>')
# def show_campaign(campaign_id):
#     the_donors = Donor.query.filter(Donor.campaign_id == campaign_id).all()
#     return flask.render_template(
#         'show_campaign.html',
#         donors=the_donors
#     )


@application.errorhandler(404)
def page_not_found(e):
    if flask_login.current_user.is_authenticated:
        return flask.render_template('index.html')
    else:
        return flask.render_template('login.html')


# @application.route('/run_names')
# def run_names():
#     start = 5970
#     finish = 5981
#     while True:
#         all_donations = Donor.query.filter(and_(Donor.Result < finish, Donor.Result > start)).all()
#         if len(all_donations) == 0:
#             return ''
#         for donation in all_donations:
#             full_name = (donation.First_Name + ' ' + donation.Last_Business_Name)
#             donation.full_name = full_name
#             print(str(donation.Result) + ' ' + full_name)
#             db.session.add(donation)
#         start += 10
#         finish += 10
#         db.session.commit()
#         print(finish)
#
#
@application.route('/run_campaigns')
def run_campaigns():
    offset = 83216
    start = 455050 + offset
    finish = 456051 + offset
    while True:
        all_donations = APOC.query.filter(and_(APOC.id < finish, APOC.id > start)).all()
        if len(all_donations) == 0:
            return ''
        for donation in all_donations:
            print(donation.id)
            the_campaign = Campaign.query.filter(Campaign.name == donation.Name).first()
            if not the_campaign:
                print('creating ' + donation.Name)
                new_campaign = Campaign()
                new_campaign.name = donation.Name
                db.session.add(new_campaign)
                db.session.commit()
        start += 1000
        finish += 1000
        print(finish)
#
# @application.route('/run_contributors')
# def run_contributors():
#     start = 0
#     finish = 1001
#     while True:
#         all_donations = Donor.query.filter(and_(Donor.Result < finish, Donor.Result > start)).all()
#         if len(all_donations) == 0:
#             return ''
#         for donation in all_donations:
#             print(donation.Result)
#             full_name = donation.First_Name + ' ' + donation.Last_Business_Name
#             the_contributor = Contributor.query.filter(Contributor.full_name == full_name).first()
#             if not the_contributor:
#                 print('creating ' + full_name)
#                 new_contributor = Contributor()
#                 new_contributor.Last_Business_Name = donation.Last_Business_Name
#                 new_contributor.First_Name = donation.First_Name
#                 new_contributor.full_name = full_name
#                 db.session.add(new_contributor)
#                 db.session.commit()
#         start += 1000
#         finish += 1000
#         print(finish)


@application.route('/api/campaigns')
def dump_campaigns():
    all_the_campaigns = Campaign.query.all()
    result = []
    for each_campaign in all_the_campaigns:
        result.append({
            'id': each_campaign.id,
            'name': each_campaign.name,
            'leans': each_campaign.leans
        })
    return json.dumps(result)


@application.route('/api/campaigns/<int:campaign_id>/')
def dump_campaign(campaign_id):
    the_donors = db.session.query(
        APOC
    )\
        .filter(APOC.campaign_id == campaign_id).group_by(APOC.van_id, APOC.Report_Year).all()
    result = []
    for each_donor in the_donors:
        result.append({
            "id": each_donor.id,
            "full_name": each_donor.full_name,
            "total_amount": int(each_donor.total_amount),
            "Report_Year": each_donor.Report_Year,
            "contributor_score": int(each_donor.contributor_score or 0),
            "avg_contribution": int(each_donor.avg_contribution or 0),
            "van_id": each_donor.van_id,
            "PreferredPhone": each_donor.PreferredPhone,
            "district": each_donor.HD
        })
    the_campaign = Campaign.query.get(campaign_id).as_dict()
    return json.dumps({'contributions': result, 'info': the_campaign})


@application.route('/api/campaigns/<int:campaign_id>/info')
def dump_campaign_info(campaign_id):
    the_campagign = Campaign.query.get(campaign_id).as_dict()
    return json.dumps(the_campagign)


@application.route('/api/contributors')
def dump_contributors():
    contributors = Contributor.query.filter(Contributor.is_person).all()
    result = []
    for each_contributor in contributors:
        result.append(each_contributor.as_dict())
    return simplejson.dumps(result, allow_nan=False)


@application.route('/api/contributors/<int:contributor_id>')
def dump_contributor(contributor_id):
    the_donors = APOC.query.filter(APOC.van_id == contributor_id).all()
    result = []
    for each_donor in the_donors:
        result.append(each_donor.as_dict())
    the_contributor = Van.query.get(contributor_id).as_dict()
    return json.dumps({'contributions': result, 'contributor': the_contributor})


@application.route('/api/contributors/<int:contributor_id>/activist_codes')
def fetch_activist_codes(contributor_id):
    the_codes = ActivistCodes.query.filter(ActivistCodes.VANID == contributor_id).all()
    result = []
    for each_code in the_codes:
        result.append(each_code.as_dict())
    return simplejson.dumps(result)


@application.route('/api/contributors/search')
def search_contributors():
    search_term = flask.request.args.get('search')
    form_submit = flask.request.args.get('formSubmit')
    return Van.find_by_name(search_term, None, form_submit)


@application.route('/api/login')
def login_user():
    params = flask.request.args
    user_id = int(params.get('id'))
    the_user = User.query.filter(User.id == user_id).first()
    if not the_user:
        the_user = User()
        the_user.id = user_id
        the_user.name = params.get('name')
        db.session.add(the_user)
        resp = the_user.serialize()
        db.session.commit()
    else:
        resp = the_user.serialize()
    return resp


@application.route('/api/voters/district/<int:district_id>')
def fetch_district_voters(district_id):
    result = ACTIVE_CACHE.get(str(district_id))
    if not result:
        voters = Van.query.filter(Van.HD == district_id).all()
        result = []
        for each_voter in voters:
            result.append(each_voter.as_dict())
        ACTIVE_CACHE[str(district_id)] = result
    return json.dumps(result)

db = SQLAlchemy(application)


class BaseModel:
    def as_dict(self):
        result = {}
        for attr, value in self.__dict__.items():
            if not value and value != 0:
                result[attr] = None
            else:
                try:
                    result[attr] = int(value)
                except Exception:
                    try:
                        result[attr] = str(value)
                    except Exception:
                        pass
        return result


class Campaign(db.Model, BaseModel):
    __tablename__ = 'campaigns'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True)
    leans = db.Column(db.String(1))
    score = db.Column(db.Float)

    def sum_contributor_score(self):
        print(self.name)
        the_contributor = Contributor.query.filter(Contributor.full_name == (' ' + self.name)).first()
        if the_contributor:
            if the_contributor.get_score() > 500:
                self.leans = 'l'
                db.session.add(self)
                db.session.commit()
                return ''
            elif the_contributor.get_score() < -500:
                self.leans = 'r'
                db.session.add(self)
                db.session.commit()
                return ''
        contributions = self.contributions
        score = 0
        update = False
        seen = {}
        for each_contribution in contributions:
            if each_contribution and each_contribution.contributor and (not seen.get(each_contribution.contributor.full_name)):
                # add_to_score = each_contribution.contributor.get_score()
                # seen[each_contribution.contributor.full_name] = True
                # if add_to_score < 0:
                #     add_to_score = -1
                #     print(self.name + ' contributor ' + each_contribution.contributor.full_name + ' leans right')
                # elif add_to_score > 0:
                #     add_to_score = 1
                #     print(self.name + ' contributor ' + each_contribution.contributor.full_name + ' leans left')
                score += each_contribution.contributor.add_to_score
                print(score)
                if (score > 10) or (score < -10):
                    break
        if score > 4:
            self.leans = 'l'
            update = True
        elif score < -4:
            self.leans = 'r'
            update = True
        print(score)
        if update:
            db.session.add(self)
            db.session.commit()


class Contributor(db.Model, BaseModel):
    __tablename__ = 'contributors'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), index=True)
    Last_Business_Name = db.Column(db.String(255))
    First_Name = db.Column(db.String(255))
    score = db.Column(db.Float)
    add_to_score = db.Column(db.Float)
    avg_score = db.Column(db.Float)
    avg_donation = db.Column(db.Float)
    total = db.Column(db.Float)
    is_person = db.Column(db.Boolean)

    def get_score(self):
        if self.score:
            return self.score
        all_contributions = self.contributions
        score = {
            'l': 0,
            'r': 0
        }
        for each_contribution in all_contributions:
            if each_contribution.campaign and each_contribution.campaign.leans:
                score[each_contribution.campaign.leans] += each_contribution.total_amount()
        result = score['l'] - score['r']
        if result != self.score:
            self.score = result
            db.session.add(self)
            db.session.commit()
            print(self.full_name + ' updated to ' + str(self.score))
        return result

    @classmethod
    def find_by_name(cls, search_term, order_by=None, form_submit=None):
        if order_by:
            order_attr = getattr(cls, order_by)
        else:
            order_attr = cls.full_name
        or_statement = or_(
            cls.full_name.ilike('%{0}%'.format(search_term))
        )
        results = cls.query.filter(or_statement).order_by(order_attr).limit(500).all()
        final_array_to_return = [x.as_dict() for x in results]
        if not len(final_array_to_return):
            final_array_to_return.append({
                "id": 0,
                "full_name": "No Results",
                "score": '-1'
            })
        final_array_to_return[0]['formSubmit'] = form_submit
        return json.dumps(final_array_to_return)


class Donor(db.Model, BaseModel):
    __tablename__ = "donors"
    Result = db.Column(db.Integer, primary_key=True)

    contributor_score = db.Column(db.Float)
    contributor_id = db.Column(db.Integer, db.ForeignKey('contributors.id'), index=True, nullable=True)

    total_amount = db.Column(db.Float)

    Date = db.Column(db.String(255))
    Transaction_Type = db.Column(db.String(255))
    Payment_Type = db.Column(db.String(255))
    Payment_Detail = db.Column(db.String(255))
    Amount = db.Column(db.String(255))
    Last_Business_Name = db.Column(db.String(255))
    First_Name = db.Column(db.String(255))
    Address = db.Column(db.String(255))
    City = db.Column(db.String(255))
    State = db.Column(db.String(255))
    Zip = db.Column(db.String(255))
    Country = db.Column(db.String(255))
    Occupation = db.Column(db.String(255))
    Employer = db.Column(db.String(255))
    Purpose_of_Expenditure = db.Column(db.String(255))
    Report_Type = db.Column(db.String(255))
    Election_Name = db.Column(db.String(255))
    Election_Type = db.Column(db.String(255))
    Municipality = db.Column(db.String(255))
    Office = db.Column(db.String(255))
    Filer_Type = db.Column(db.String(255))
    Name = db.Column(db.String(255), index=True, nullable=True)
    Report_Year = db.Column(db.String(255))
    Submitted = db.Column(db.String(255))
    lean = db.Column(db.String(1))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), index=True, nullable=True)
    full_name = db.Column(db.String(255), index=True, nullable=True)
    # campaign = db.relationship(
    #     'Campaign',
    #     backref=db.backref('contributions', lazy='dynamic')
    # )
    # contributor = db.relationship(
    #     'Contributor',
    #     backref=db.backref('contributions', lazy='dynamic')
    # )

    def __init__(self):
        self.full_name = self.First_Name + ' ' + self.Last_Business_Name
        self.is_person = bool(self.First_Name and len(self.First_Name) > 0)

    def leans(self):
        if self.lean:
            return self.lean
        else:
            return self.campaign.leans


class Voter(db.Model, BaseModel):
    __tablename__ = 'alaska'
    id = db.Column(db.Integer, primary_key=True)
    district = db.Column(db.Integer)
    RESIDENCE_ZIP = db.Column(db.Integer)
    voter_score = db.Column(db.Integer)
    full_name = db.Column(db.String(255), index=True)
    RESIDENCE_ADDRESS = db.Column(db.String(255))
    RESIDENCE_CITY = db.Column(db.String(255))
    contributor_id = db.Column(db.Integer, db.ForeignKey('contributors.id'), index=True, nullable=True)
    precinct = db.Column(db.Integer)
    PARTY = db.Column(db.String(255))

    VANID = db.Column(db.Integer)
    PreferredEmail = db.Column(db.String(255))
    PreferredPhone = db.Column(db.String(255))

    # contributor = db.relationship(
    #     'Contributor',
    #     backref=db.backref('voter_contributions', lazy='dynamic')
    # )

    score = db.Column(db.Float)
    score_guess = db.Column(db.Float)


class Van(db.Model, BaseModel):
    __tablename__ = 'van'

    VANID = db.Column(db.Integer, primary_key=True)
    PreferredEmail = db.Column(db.String(255))
    PreferredPhone = db.Column(db.String(255))
    full_name = db.Column(db.String(255))
    HD = db.Column(db.String(255))
    SD = db.Column(db.String(255))
    party = db.Column(db.String(255))
    vAddress = db.Column(db.String(255))
    City = db.Column(db.String(255))
    State = db.Column(db.String(255))
    Zip5 = db.Column(db.String(255))
    Zip4 = db.Column(db.String(255))

    donor_score = db.Column(db.Integer)
    score_guess = db.Column(db.Integer)
    avg_contribution = db.Column(db.Integer)
    total_amount = db.Column(db.Integer)
    precinct = db.Column(db.Integer)
    num_contributions = db.Column(db.Integer)
    num_votes = db.Column(db.Integer)
    gave_to_adp = db.Column(db.Integer)

    @classmethod
    def find_by_name(cls, search_term, order_by=None, form_submit=None):
        if order_by:
            order_attr = getattr(cls, order_by)
        else:
            order_attr = cls.full_name
        or_statement = and_(
            cls.full_name.ilike('%{0}%'.format(search_term)),
            cls.num_contributions > 0
        )
        results = cls.query.filter(or_statement).order_by(order_attr).limit(500).all()
        final_array_to_return = [x.as_dict() for x in results]
        if not len(final_array_to_return):
            final_array_to_return.append({
                "id": 0,
                "full_name": "No Results",
                "score": '-1'
            })
        final_array_to_return[0]['formSubmit'] = form_submit
        return json.dumps(final_array_to_return)


    # contributor = db.relationship(
    #     'Contributor',
    #     backref=db.backref('voter_contributions', lazy='dynamic')
    # )

class ActivistCodes(db.Model, BaseModel):
    __tablename__ = 'activist_codes'

    ActivistCodeID = db.Column(db.Integer, primary_key=True)
    VANID = db.Column(db.Integer)
    ActivistCodeName = db.Column(db.String(255))
    ActivistCodeDescription = db.Column(db.String(255))
    DateCreated = db.Column(db.String(255))


class APOC(db.Model, BaseModel):
    __tablename__ = 'apoc'

    id = db.Column(db.Integer, primary_key=True)
    van_id = db.Column(db.Integer, db.ForeignKey('van.VANID'))
    van = db.relationship(
        'Van',
        backref=db.backref('contributions', lazy='dynamic')
    )

    #begin copypasta
    Result = db.Column(db.Integer)
    Date = db.Column(db.String(255))
    Transaction_Type = db.Column(db.String(255))
    Payment_Type = db.Column(db.String(255))
    Payment_Detail = db.Column(db.String(255))
    Amount = db.Column(db.String(255))
    Last_Business_Name = db.Column(db.String(255))
    First_Name = db.Column(db.String(255))
    Address = db.Column(db.String(255))
    City = db.Column(db.String(255))
    State = db.Column(db.String(255))
    Zip = db.Column(db.String(255))
    Country = db.Column(db.String(255))
    Occupation = db.Column(db.String(255))
    Employer = db.Column(db.String(255))
    Purpose_of_Expenditure = db.Column(db.String(255))
    Report_Type = db.Column(db.String(255))
    Election_Name = db.Column(db.String(255))
    Election_Type = db.Column(db.String(255))
    Municipality = db.Column(db.String(255))
    Office = db.Column(db.String(255))
    Filer_Type = db.Column(db.String(255))
    Name = db.Column(db.String(255), index=True, nullable=True)
    Report_Year = db.Column(db.String(255))
    Submitted = db.Column(db.String(255))

    contributor_score = db.Column(db.Float)
    avg_contribution = db.Column(db.Integer)
    HD = db.Column(db.Integer)
    contributor_id = db.Column(db.Integer, db.ForeignKey('contributors.id'), index=True, nullable=True)
    total_amount = db.Column(db.Float)
    lean = db.Column(db.String(1))
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaigns.id'), index=True, nullable=True)
    full_name = db.Column(db.String(255), index=True, nullable=True)
    PreferredPhone = db.Column(db.String(255))



class User(db.Model, BaseModel, flask_login.UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, index=True)
    name = db.Column(db.String(255), index=True)
    password = db.Column(db.String(255))

    def serialize(self):
        return json.dumps({
            "id": self.id,
            "name": self.name
        })


def execute_sql(query):
    db.session.execute(query)


def execute_queries(queries):
    for query in queries:
        execute_sql(query)

if __name__ == '__main__':
    application.run(debug=True)

from appModule import app, db, bcrypt,api
from flask_restful import Resource, reqparse
from sklearn.cluster import KMeans
from sklearn.preprocessing import normalize
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import ValidationError
from models import User, Concepts, ConceptsSchema, Article, ArticleSchema
from ml import embedding
from ml import kde
from flask import request, jsonify, session



schema = ConceptsSchema()
article_list_schema = ArticleSchema(only=('published_date','title','type','section','id','comments_count'), many=True)
article_schema = ArticleSchema()



headerNames = ['word'] + range(300)
wordsFileName = './data/glove.6B.300d.txt'
# wordsFileName = './data/glove.6B.50d.txt' # for testing

# unified w2v queries with caching
# w2v_model = embedding.EmbeddingModel(wordsFileName)
# kde_model = kde.KdeModel(w2v_model)


@app.after_request
def after_request(response):
	# pdb.set_trace()
	response.headers.add('Access-Control-Allow-Origin', '*')
	response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
	response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
	return response



class RecommendWordsCluster(Resource):

	def post(self):
		try:
			# pdb.set_trace()
			parser = reqparse.RequestParser()
			parser.add_argument('positiveWords', type=unicode, action='append', required=True, help="Positive words cannot be blank!")
			parser.add_argument('negativeWords', type=unicode, action='append', help='Negative words')

			args = parser.parse_args()

			# pdb.set_trace()

			positive_terms = args['positiveWords']

			positive_terms = [w.encode('UTF-8') for w in positive_terms]
			negative_terms = args['negativeWords']

			# Because pairwise distance computations are cached in the w2v_model,
			# we do not need to worry about re-training the kde model
			#
			# Note: You can later put irr_words (see the function)
			kde_model.learn(h_sq=0.2, pos_words=positive_terms,
											neg_words=negative_terms, irr_words=[])

			positive_recommend = kde_model.recommend_pos_words(how_many=50)
			negative_recommend = kde_model.recommend_neg_words(how_many=50)

			# currently i didn't put the clustering yet
			return jsonify(positiveRecommend=positive_recommend,
										 negativeRecommend=negative_recommend)


		except Exception as e:
			# pdb.set_trace()
			return {'error': str(e)}

class QueryAutoComplete(Resource):
  def get(self, word):
    wordUTF8 = word.encode('UTF-8')
    # import pdb; pdb.set_trace()
    new_list = w2v_model.getAutoComplete(wordUTF8)
    return {'word': new_list}

class Register(Resource):
	def post(self):

		# Parse the arguments
		parser = reqparse.RequestParser()
		# import pdb; pdb.set_trace()
		parser.add_argument('name', type=str, help="User name to be called")
		parser.add_argument('email', type=str, help='Email address to create user')
		parser.add_argument('password', type=str, help='Password to create user')

		args = parser.parse_args()

		_userName = args['name']
		_userEmail = args['email']
		_userPassword = args['password']

		user = User(name=_userName, email=_userEmail, password=_userPassword)
		try:
			db.session.add(user)
			db.session.commit()
			status = 'success'

		except Exception as e:
			# pdb.set_trace()
			status = 'This user is already registered'
			db.session.close()

		return {'result': status}

class Login(Resource):
	def post(self):
		try:
			# Parse the arguments

			parser = reqparse.RequestParser()
			parser.add_argument('email', type=str, help='Email address for Authentification')
			parser.add_argument('password', type=str, help='Password for Authentication')
			args = parser.parse_args()

			_userEmail = args['email']
			_userPassword = args['password']

			user = User.query.filter_by(email=_userEmail).first()
			if user and bcrypt.check_password_hash(user.password, _userPassword):
				session['logged_in'] = True
				session['user'] = user.id
				session['userName'] = user.name
				status = True
			else:
				status = False

			# pdb.set_trace()
			return jsonify({'result':status, 'name': user.name})
		except Exception as e:
			# pdb.set_trace()
			return {'error':str(e)}

class Logout(Resource):
	def get(self):
		try:
			# Parse the arguments
			session.pop('logged_in', None)
			session.pop('user', None)
			session.pop('userName', None)

			return {'result':'success'}
		except Exception as e:
			return {'error':str(e)}

class Status(Resource):
	def get(self):
		# pdb.set_trace()
		if session.get('logged_in'):
			if session['logged_in']:
				return {'status':True, 'user': session['user'], 'userName':session['userName']}
		else:
			return {'status':False}

class ConceptList(Resource):
	def get(self):
		concepts_query = Concepts.query.all()
		results =  schema.dump(concepts_query, many=True).data
		return results

	def post(self):
		raw_dict = request.get_json(force=True)
		# import pdb; pdb.set_trace()
		try:
			schema.validate(raw_dict)
			concept_dict = raw_dict['data']['attributes']
			# import pdb;pdb.set_trace()

			if session.get('logged_in'):
				userID = session['user']
				userName = session['userName']
			else:
				return {'status':"UnAuthorized Access for Post ConceptList"}

			concept = Concepts(concept_dict['name'], userID, concept_dict['concept_type'], concept_dict['input_terms'], userName)
			concept.add(concept)

			query = Concepts.query.get(concept.id)
			results = schema.dump(query).data

			return results, 201

		except ValidationError as err:
			resp = jsonify({"error":err.messages})
			resp.status_code = 403
			return resp

		except SQLAlchemyError as e:
			db.session.rollback()
			resp = jsonify({"error": str(e)})
			resp.status_code = 403
			return resp


class ConceptsUpdate(Resource):
	def get(self,id):
		concept_query = Concepts.query.get_or_404(id)
		result = schema.dump(concept_query).data
		# import pdb;pdb.set_trace()
		return result

	def patch(self,id):
		concept = Concepts.query.get_or_404(id)
		raw_dict = request.get_json(force=True)

		try:
			schema.validate(raw_dict)
			concept_dict = raw_dict['data']['attributes']

			for key, value in concept_dict.items():
				setattr(concept, key, value)

			concept.update()
			return self.get(id)

		except ValidationError as err:
			resp = jsonify({"error":err.messages})
			resp.status_code = 401
			return resp

		except SQLAlchemyError as e:
			db.session.rollback()
			resp = jsonify({"error": str(e)})
			resp.status_code = 401
			return resp

	def delete(self, id):
		concept = Concepts.query.get_or_404(id)
		try:
			delete = concept.delete(concept)
			concepts_query = Concepts.query.all()
			results =  schema.dump(concepts_query, many=True).data
			return results
		except SQLAlchemyError as e:
			db.session.rollback()
			resp = jsonify({"error": str(e)})
			resp.status_code = 401
			return resp

class ArticleList(Resource):
	def get(self):
		articles_query = Article.query.all()
		results =  article_list_schema.dump(articles_query).data
		return results

	
class ArticleUpdate(Resource):
	def get(self,id):
		concept_query = Concepts.query.get_or_404(id)
		result = article_schema.dump(concept_query).data
		# import pdb;pdb.set_trace()
		return result


api.add_resource(Register, '/api/register')
api.add_resource(Login, '/api/login')
api.add_resource(Logout, '/api/logout')
api.add_resource(QueryAutoComplete, '/api/QueryAutoComplete/<string:word>')
api.add_resource(RecommendWordsCluster, '/api/RecommendWordsCluster')
api.add_resource(Status, '/api/status')
api.add_resource(ConceptList, '/api/concepts')
api.add_resource(ConceptsUpdate, '/api/concepts/<int:id>')
api.add_resource(ArticleList, '/api/articles')
api.add_resource(ArticleUpdate, '/api/articles/<int:id>')


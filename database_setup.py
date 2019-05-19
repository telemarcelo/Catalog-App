import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()
#end of beginning code

class Category(Base):
	__tablename__='Category'
	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)

class User(Base):
	__tablename__='User'
	name = Column(String(80), nullable = False)
	email = Column(String(80), nullable = False)
	picture = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)	

class Item(Base):
	__tablename__='Item'
	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	description = Column(String(250))
	category_id = Column(Integer, ForeignKey('Category.id'))
	category = relationship(Category)
	user_id = Column(Integer, ForeignKey('User.id'))
	user = relationship(User)


# at end of file
engine = create_engine('sqlite:///ItemCatalog.db')
Base.metadata.create_all(engine)
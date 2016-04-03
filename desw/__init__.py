import imp
import logging
import os
import sys
import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy_login_models.model import UserKey, User as SLM_User
import model

import ConfigParser
CFG = ConfigParser.ConfigParser()
CFG.read(os.environ.get('DESW_CONFIG_FILE', 'example_cfg.ini'))

# Setup database
eng = sa.create_engine(CFG.get('db', 'SA_ENGINE_URI'))
ses = orm.sessionmaker(bind=eng)()

def setup_database():
    SLM_User.metadata.create_all(eng)
    UserKey.metadata.create_all(eng)
    for m in model.__all__:
        getattr(model, m).metadata.create_all(eng)

setup_database()

models = model # rename loaded models to avoid ambiguity

# Setup logging
logfile = CFG.LOGFILE if hasattr(CFG, 'LOGFILE') else 'server.log'
loglevel = CFG.LOGLEVEL if hasattr(CFG, 'LOGLEVEL') else logging.INFO
logging.basicConfig(filename=logfile, level=loglevel)
logger = logging.getLogger(__name__)


__all__ = ['eng', 'ses', 'CFG', 'logger', 'models']


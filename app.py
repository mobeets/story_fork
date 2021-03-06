import os
import json
import cherrypy
from mako.lookup import TemplateLookup

import conf
from bin.db_connect import Engine
from bin.model import StoryForkData, PRE_ROOT_TINE_ID, BASE_USER, URL, fake_story

def int_or_neg(int_str):
    try:
        return int(int_str)
    except ValueError:
        return -1
    except TypeError:
        return -1

lookup = TemplateLookup(directories=['templates'])
class Root(object):
    def __init__(self, datastore, db):
        self.datastore = datastore
        self.db = db

    @cherrypy.expose
    def default(self, *data):
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def index(self, *data):
        tmp = lookup.get_template('index.html')
        return tmp.render(story_list=self.datastore.story_data.values(), error_msg='')

    @cherrypy.expose
    def view(self, story_index=None, tine_index=None, *data):
        title = 'Story Fork'
        error_msg = ''
        data = None
        story_index = int_or_neg(story_index)
        tine_index = int_or_neg(tine_index)
        if story_index in self.datastore.story_data:
            story = self.datastore.story_data[story_index]
            story_name = story.root_tine.content
            title = 'Story {0}: {1}'.format(story_index, story.root_tine.content)
            # data = story.to_json()
        else:
            error_msg = 'Story fork no. {0} could not be found.'.format(story_index)
        tmp = lookup.get_template('story_fork.html')
        return tmp.render(title=title, error_msg=error_msg, story_index=story_index, tine_index=tine_index)

    @cherrypy.expose
    def load_data(self, story_index):
        story_index = int_or_neg(story_index)
        if story_index in self.datastore.story_data:
            story = self.datastore.story_data[story_index]
            title = 'Story {0}: {1}'.format(story_index, story.root_tine.content)
            return json.dumps(story.to_json())
        return json.dumps({})

    @cherrypy.expose
    def tine_path(self, story_index=None, tine_index=None, *data):
        story_index = int_or_neg(story_index)
        tine_index = int_or_neg(tine_index)
        tines = []
        if story_index in self.datastore.story_data:
            story = self.datastore.story_data[story_index]
            if tine_index in story.tines:
                leaf_tine = story.tines[tine_index]
                cur_tine = leaf_tine
                while cur_tine:
                    tines.append(cur_tine.content)
                    # content = cur_tine.content + '<br>' + content
                    cur_tine = cur_tine.parent_tine
                for i, tine in enumerate(tines):
                    if i == 0:
                        tines[i] = '<span id="leaf_tine">{0}</span>'.format(tine)
                    elif i == len(tines)-1:
                        tines[i] = '<span id="root_tine">{0}</span>'.format(tine)
                    else:
                        tines[i] = '<span id="mid_tine">{0}</span>'.format(tine)
                content = '<br>'.join(tines[::-1])
                return '<h3>The story so far:</h3><div id="story_content">{0}</div><hr>'.format(content)
        return ''

    @cherrypy.expose
    def tine_embedded(self, story_index=None, tine_index=None, *data):
        story_index = int_or_neg(story_index)
        tine_index = int_or_neg(tine_index)
        if story_index in self.datastore.story_data:
            story = self.datastore.story_data[story_index]
            if tine_index in story.tines:
                tine = story.tines[tine_index]
                return tine.embed['html']
        return ''

    @cherrypy.expose
    def update(self, extra, *data):
        if extra == 'pleasedoit':
            print self.datastore.print_status()
            print 'UPDATING TWEETS AND STORIES'
            self.datastore.update()
            print self.datastore.print_status()
            self.commit('pleasedoit')
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def commit(self, extra, *data):
        if extra == 'pleasedoit':
            # print 'QUERYING'
            # print StoryForkData.singleton(self.db).print_status()
            print 'COMMITTING'
            self.db.commit()
            print self.datastore.print_status()
            # print 'QUERYING'
            # print StoryForkData.singleton(self.db).print_status()
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def clear(self, extra, *data):
        if extra == 'pleasedoit':
            print self.datastore.print_status()
            print 'CLEARING STORIES'
            self.datastore.clear_stories()
            # self.datastore.clear_all()
            print self.datastore.print_status()
            self.commit('pleasedoit')
        raise cherrypy.HTTPRedirect("/")

    @cherrypy.expose
    def create(self, *data):
        story_index = self.datastore.get_next_story_index()
        return self.tweet_link(story_index, PRE_ROOT_TINE_ID, is_root=True)

    @cherrypy.expose
    def reply(self, story_index=None, tine_index=None, *data):
        story_index = int_or_neg(story_index)
        tine_index = int_or_neg(tine_index)
        link = self.tweet_link(story_index, tine_index)
        if link:
            return """<table><tr><td>{0}</td><td> and <a href="/update/pleasedoit">update</a> and the next sentence is yours.</td></tr></table>""".format(link)
        return ''

    def tweet_link(self, story_index, tine_index, is_root=False, text='Your sentence here!'):
        url = URL + str(story_index) + '/' + str(tine_index)
        valid = is_root
        if story_index in self.datastore.story_data:
            story = self.datastore.story_data[story_index]
            if tine_index in story.tines:
                valid = True
        if not valid:
            return ''
        return """<a href="https://twitter.com/intent/tweet?screen_name={user}&text={text}"
            class="twitter-mention-button"
            data-size="large"
            data-related="{user}"
            data-url="{url}">(Click here)
            </a>""".format(text=text, user=BASE_USER, url=url)

def inner_main(db):
    db.create_singleton_if_not_exists(StoryForkData, StoryForkData.empty_singleton)
    db_session = db.session()
    datastore = StoryForkData.singleton(db_session)
    # datastore.update()
    db_session.commit()
    print datastore.print_status()
    return Root(datastore, db_session)

def main():
    cherrypy.config.update(conf.settings)
    
    db_engine = Engine()
    story_fork_app = inner_main(db_engine)
    root_app = cherrypy.tree.mount(story_fork_app, '/', conf.root_settings)
    root_app.merge(conf.settings)

    if hasattr(cherrypy.engine, "signal_handler"):
        cherrypy.engine.signal_handler.subscribe()
    if hasattr(cherrypy.engine, "console_control_handler"):
        cherrypy.engine.console_control_handler.subscribe()
    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    main()

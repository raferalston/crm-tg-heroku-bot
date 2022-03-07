import datetime
import requests 
import json
import functools


#TODO:(Mike) move API to the os environment 
with open('ACCESS.json') as f:
    ACCESS_GRANTED = json.load(f) 

with open('Managers.json') as f:
    MANAGERS = json.load(f) 

with open('CRM_KEY') as f:
    API_KEY = f.read()

def token_decorator(method):
    """decorator for token creation and revoke"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        self.get_access_token()
        result = method(self, *args, **kwargs)
        self.revoke_token()
        return result
    return wrapper

def chat_permission(method):
    """decorator for check chat permission"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        _teacher = kwargs.get('teacher', 'limited')
        if str(_teacher) in ACCESS_GRANTED:
            kwargs['teacher'] = {_teacher: 'full'}
        else:
            kwargs['teacher'] = {_teacher: 'limited'}
        result = method(self, *args, **kwargs)
        return result
    return wrapper

def chat_auth(method):
    """decorator for token creation and revoke"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        flag = False
        _keys = kwargs.copy().get('access').keys()
        for k in _keys:
            if str(k) in MANAGERS.keys():
                flag = True 
        if flag:
            result = method(self, *args, **kwargs)
        else:
            result = 'Тут ничего нет, ищи на kidkod.ru'
        return result
    return wrapper

class CRM_API:
    def __init__(self, API_KEY):
        self.API_KEY = API_KEY
        self.urls = {
            'GET_TOKEN': 'https://api.moyklass.com/v1/company/auth/getToken',
            'REVOKE_TOKEN': 'https://api.moyklass.com/v1/company/auth/revokeToken',
            'GET_LESSONS': 'https://api.moyklass.com/v1/company/lessons',
            'GET_LESSON_BY_ID': 'https://api.moyklass.com/v1/company/lessons/',
            'GET_MANAGERS': 'https://api.moyklass.com/v1/company/managers',
            'GET_GROUPS': 'https://api.moyklass.com/v1/company/classes',
            'POST_USERS': 'https://api.moyklass.com/v1/company/users',
            'USER_INFO': 'https://api.moyklass.com/v1/company/users/%s'
        }
        self.token = None
        self.api_data = {'apiKey': API_KEY}
        self.request_json = {}

    def __str__(self):
        """Name description for this class"""
        return f'CRM class for Solncevo school'

    def get_access_token(self):
        """This method should execute first"""
        # TODO:(mike) add logger
        r = requests.post(self.urls['GET_TOKEN'], json=self.api_data) 
        # assert r.status_code == 200, 'Error in revoke_token method'
        pastebin_url = r.json() 
        revoke_token = pastebin_url['accessToken']
        self.token = revoke_token

    def revoke_token(self):
        """revokes token method"""
        # TODO:(mike) add logger
        # assert self.revoke_token, 'No revoke token available in revoke_token'
        r = requests.post(self.urls['REVOKE_TOKEN'], headers={'x-access-token': self.token}) 
        # assert r.status_code == 204, 'Error in revoke_token method'

    @token_decorator
    def get_lessons(self, _date):
        """return lessons"""
        # assert self.revoke_token, 'No revoke token available in get_lessons'
        # TODO:(mike) add logger
        date_format = _date
        r = requests.get(self.urls['GET_LESSONS'], params={'date': date_format}, headers={'x-access-token': self.token}) 
        data = r.json()
        lessons = data['lessons']
        return lessons

    @token_decorator
    def get_lesson(self, pk):
        """return lesson
        includeRecords - query param for getting lesson with students in it"""
        # assert self.revoke_token, 'No revoke token available in get_lessons'
        # TODO:(mike) add logger
        r = requests.get(self.urls['GET_LESSON_BY_ID'] + str(pk) + f'?includeRecords=true', headers={'x-access-token': self.token}) 
        data = r.json()
        return data

    @token_decorator
    def get_student_data(self, user_id):
        """return lessons"""
        # assert self.revoke_token, 'No revoke token available in get_lessons'
        # TODO:(mike) add logger
        _url = self.urls['USER_INFO']
        r = requests.get(_url % user_id, headers={'x-access-token': self.token}) 
        data = r.json()
        return data

    def get_student_name(self, lesson):
        """return name if only 1 name in group"""
        records = lesson.get('records', None)
        student_names = []
        if 0 < len(records) < 2:
            user_id = records[0].get('userId', None)
            student_name = self.get_student_data(user_id)
            return student_name.get('name', 'Без Имени')

    @token_decorator
    def get_managers(self):
        """return managers"""
        # TODO:(mike) add logger
        r = requests.get(self.urls['GET_MANAGERS'], headers={'x-access-token': self.token}) 
        data = r.json()
        return data

    @token_decorator
    def get_groups(self):
        """return groups"""
        # TODO:(mike) add logger
        r = requests.get(self.urls['GET_GROUPS'], headers={'x-access-token': self.token}) 
        data = r.json()
        return data
    

class CRM_TaskMaster(CRM_API):
    """options: list of strings, with sequence of necessary elements in telegram response.
    available options: beginTime, name, personal_name
    """
    def __init__(self, API_KEY, options=['beginTime', 'name', 'personal_name']):
        super().__init__(API_KEY)
        self.options = options

    def _set_options(self, options):
        """input: options as list with necessary items
        output: formatted string: '{item1} - {item2} - {item...}'"""
        return ' - '.join(map(lambda opt: '{%s}' % opt, options))
    
    def _managers_to_dict(self, managers):
        teachers = {}
        for teacher in managers:
            number = teacher['id']
            name = teacher['name']
            teachers[number] = name
        return teachers

    @chat_auth
    def _schedule_builder(self, _date, access):
        """input:
        output: schedule as string"""
        # TODO: input lessons, groups as args* for refactor this as strategy pattern. 
        # TODO: write a scheme for output pattern (left is more important than right). Example: teacher: date: lessons: ...
        # TODO: make an option response template {name: (args*), ...} 
        schedule = None
        response_string = f'*Расписание на {_date.strftime("%A")} {_date}*\n'
        _lessons = self.get_lessons(_date)
        _groups = self.get_groups()
        _managers = self._managers_to_dict(self.get_managers())
        _options = self._set_options(self.options)
        _chatid, _access = access.popitem()
        _id = MANAGERS.get(str(_chatid))
        schedule = self._chat_dispatcher(_access, _id, _date, _lessons, _managers, _groups)
        for tchr in schedule:
            response_string += u'\n\U0001F393' + \
                f'*{tchr}*\n' + ''.join(map(lambda item: u'\U0000231A' + _options.format(**item) + '\n', 
                sorted(schedule[tchr], key=lambda k: k['beginTime'])))
        
        if len(response_string.splitlines()) == 1:
            response_string += u'\U0001F634' + 'В этот день занятий нет.\n'

        return response_string

    def _chat_dispatcher(self, _access, _id, _date, _lessons, _managers, _groups):
        """input: 
        output: schedule as dict"""
        schedule = {}
        if _access == 'full':
            schedule = self._full_access_schedule(_id, _date, _lessons, _managers, _groups)
        elif _access == 'limited':
            schedule = self._limited_access_schedule(_id, _date, _lessons, _managers, _groups)
        return schedule

    def _full_access_schedule(self, ids, date, lessons, managers, groups):
        """return schedule as dict {name: [{option: value}, ...]}"""
        schedule = {}
        for lesson in lessons:
            lesson_date = datetime.datetime.strptime(lesson['date'], '%Y-%m-%d').date()
            if lesson_date == date:
                try:
                    tchr = lesson['teacherIds'][0]
                except IndexError:
                    continue
                if tchr in managers:
                    group_id = lesson['classId']
                    for group in groups:
                        if group['id'] == group_id:
                            student_name  =  self.get_student_name(self.get_lesson(lesson['id']))
                            if managers[tchr] not in schedule:
                                schedule[managers[tchr]] = [{
                                    'beginTime': lesson['beginTime'], 
                                    'name': group['name'],
                                    'personal_name': student_name}
                                    ]
                            else:
                                schedule[managers[tchr]].append({
                                    'beginTime': lesson['beginTime'], 
                                    'name': group['name'],
                                    'personal_name': student_name}
                                )
        return schedule

    def _limited_access_schedule(self, ids, date, lessons, managers, groups):
        """return schedule as dict {name: [{option: value}, ...]}"""
        schedule = {}
        for lesson in lessons:
            lesson_date = datetime.datetime.strptime(lesson['date'], '%Y-%m-%d').date()
            try:
                lesson['teacherIds'][0]
            except IndexError:
                continue
            if lesson_date == date and lesson['teacherIds'][0] == ids: # NOTE: this line check single teacher response
                tchr = lesson['teacherIds'][0]
                if tchr in managers:
                    group_id = lesson['classId']
                    for group in groups:
                        if group['id'] == group_id:
                            if managers[tchr] not in schedule:
                                schedule[managers[tchr]] = [{
                                    'beginTime': lesson['beginTime'], 
                                    'name': group['name'],
                                    'personal_name': ''}
                                    ]
                            else:
                                schedule[managers[tchr]].append({
                                    'beginTime': lesson['beginTime'], 
                                    'name': group['name'],
                                    'personal_name': ''}
                                )
        return schedule

    @chat_permission
    def build_schedule_tomorrow(self, teacher):
        """input: teacher as int representation of teacher telegram chat id
        output: schedule as string, for represented day"""
        _date = datetime.date.today() + datetime.timedelta(days=1)
        return self._schedule_builder(_date, access=teacher)

    @chat_permission
    def build_schedule_today(self, teacher):
        """input: teacher as int representation of teacher telegram chat id
        output: schedule as string, for represented day"""
        _date = datetime.date.today()
        return self._schedule_builder(_date, access=teacher)

    @chat_permission
    def build_schedule_aftertomorrow(self, teacher):
        """input: teacher as int representation of teacher telegram chat id
        output: schedule as string, for represented day"""
        _date = datetime.date.today() + datetime.timedelta(days=2)
        return self._schedule_builder(_date, access=teacher)

crm_dispatcher = CRM_TaskMaster(API_KEY=API_KEY)

import config_db_fiddle
import re
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException, ElementNotSelectableException, ElementNotVisibleException
from datetime import datetime

class WebHandler():
    __WAIT_LONG      = 7
    __WAIT_SHORT     = 2
    
    def __init__(self, driver):
        self.driver = driver
        #references to each question tab in webdriver
        self.leet_win = None
        self.db_win = None
        self.solution_win = None

    def get_question_elements(self):
        '''
        From the leetcode website, captures question data
        '''
        url = 'https://leetcode.com/problemset/database/?'
        win = self.open_new_win(url)
        try:
            print('\nDownloading leetcode question elements')
            #view all problems, not just first 50
            WebDriverWait(self.driver, self.__WAIT_LONG).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="question-app"]/div/div[2]/div[2]/div[2]/table/tbody[2]/tr/td/span[1]/select/option[4]'))).click()
            #note that this element can only be found using selenium (not requests, or beautifulsoup)because the table is generated after the fact in js
            element = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.presence_of_element_located((By.CLASS_NAME, 'reactable-data')))

            text =  [' '.join(line.split()) for line in element.text.split('\n')]
            question_elements = {}

            for i, line in enumerate(text):
                if (i+1) % 3 == 0:
                    q_num = int(text[i-2])
                    level = line.split()[1].lower()
                    q_name = text[i-2] + ': ' + text[i-1] + ', ' + level
                    question_elements[q_num] = {'level':level, 'name':q_name}
            self.close_window(win)
            return question_elements
        except:
            print('\n Could not find elements for SQL list from leetcode.com')

    def close_window(self, window):
        try:
            if len(self.driver.window_handles) > 1:
                self.driver.switch_to.window(window)
                self.driver.close()
        except:
            pass

    def close_question_windows(self):
        windows =  (self.leet_win, self.db_win, self.solution_win)
        for window in windows:
            if window is not None:
                self.close_window(window)
        self.leet_win = self.db_win = self.solution_win = None

    def close_all(self):
        try:
            self.driver.quit()
        #driver already quit
        except:
            print('\nCannot close driver, driver has already closed')

    def get_last_window(self):
        return self.driver.window_handles[-1]

    def reset_curr_window(self):
        try:
            self.driver.switch_to_window(self.get_last_window()) 
        except:
            pass

    def open_new_win(self, url):
        '''
        Open a new tab for specified url
        Note that driver.current_window_handle attribute is not updated when executing this
        '''
        # need to always reset to an active window before opening new window b/c if opening from an inactive window, a non such window exception is triggered
        self.reset_curr_window()
        url = '\'' + url + '\''
        script = "window.open({url})".format(url=url)
        self.driver.execute_script(script)
        self.reset_curr_window()
        return self.get_last_window()

    def is_valid_save_url(self, url):
        '''
        Check if url is a saved db-fiddle. It needs to start with https://db-fiddle, and end with a /0-9
        '''
        if re.search(r'^https://www\.db-fiddle.*/\d+$', url) is not None:
            return True
        return False

    def open_newest_fiddle_url(self, url):
        '''
        Gets the newest version of the fiddle url
        Each saved fiddle url ends with a version #, and increments up each time its saved again
        If the fiddle url redirects to db-fiddle.com that means the previous version was the last version saved
        Note: I tried using requests module to check if url is valid, but even when the url is redirected, the request.is_redirect flag is still False
        '''
        url_index = int(url[-1])
        base_url = url[:-1]
        window_handles = []

        while url != 'https://www.db-fiddle.com/':
            window_handles.append(self.open_new_win(base_url + str(url_index)))
            time.sleep(self.__WAIT_SHORT)
            url = self.driver.current_url
            url_index += 1

        # window_handles[-1] is always an invalid link that redirects to 'db-fiddle.com'
        self.db_win = window_handles[-2]

        for window in window_handles:
            if window != self.db_win:
                self.close_window(window)
        return base_url + str(url_index - 2)

    def open_solution_win(self, q_num):
        q_num = '\'' + str(q_num).zfill(4) + '\''
        try:
            url = 'https://github.com/kamyu104/LeetCode-Solutions#sql'
            self.solution_win = self.open_new_win(url)
            #find question from github page
            WebDriverWait(self.driver, self.__WAIT_LONG).until(EC.element_to_be_clickable((By.XPATH,("//*[contains(text(),{q_num})]/following-sibling::td/following-sibling::td".format(q_num=q_num))))).click()
            #find solution text, and scroll to it
            element = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[itemprop="text"]')))
            self.driver.execute_script("arguments[0].scrollIntoView();", element)
        except:
            print('\nSolution not found')


    def get_leetcode_url(self, q_num):
        return 'https://leetcode.jp/problemdetail.php?id={q_num}'.format(q_num=q_num)

    def open_leetcode_win(self, q_num):
        '''
        select the leetcode jp problem to go to
        '''
        self.leet_win = self.open_new_win(self.get_leetcode_url(q_num))

    class TableParser:
        __WAIT_LONG      = 7
        __WAIT_SHORT     = 2

        def __init__(self, driver):
            self.driver = driver

        def parse_table_pre(self):
            #find sql text tables using pre element tag
            elements_pre = self.driver.find_elements_by_css_selector("pre")
            tables_pre = [element.text for element in elements_pre]

            #use list() to make a copy so that removal of elements does not effect loop indexing
            for table_pre in list(tables_pre):
                #remove data type tables
                if 'Column Name' in table_pre:
                    tables_pre.remove(table_pre)
            return tables_pre

        def parse_table_lines(self, tables_pre):
            '''
            tables_pre will contain some extra non-table lines
            This will remove any line that is not part of a table.
            The returned list will still need to be cleaned because the tables aren't seperated out
            '''
            table_lines = []
            for table_pre in tables_pre:
                pattern = re.compile('\+--*.*\+|\|.*\|')
                table_lines.append(pattern.findall(table_pre))
            return table_lines

        def is_table1(self, table_lines):
            '''
            Table 1 are from newer questions where each line is sep by +---
            '''
            return '+' in table_lines[0][0]

        def add_filler_col1(self, index, line, is_final=False):
            '''
            DB-fiddle does not support text to DDL for tables with 1 column. This adds a filler column for type 1 tables
            '''
            if index == 0:
                concat = '---------+'
            elif index == 1:
                concat = ' ignore  |'
            elif index == 2:
                concat = '---------+'
            elif is_final:
                concat = '---------+'
            else:
                concat = '  _      |'
            return line + concat

        def add_filler_col2(self, index, line):
            '''
            DB-fiddle does not support text to DDL for tables with 1 column. This adds a filler column for type 2 tables
            '''
            if index == 0:
                concat = ' ignore|'
            elif index == 1:
                concat = '-------|'
            else:
                concat = '   _   |'
            return line + concat
        
        def replace_invalid_char_header(self, line):
            '''
            for each non-valid char match, returns a space 
            The inner function adds a space for every match, rather than just one space for all matches
            '''
            #valid characters for tables names | valid characters for tables
            pattern = re.compile(r'[^_A-Za-z\s\|\+\-]+')
            def repl(m):
                return ' ' * len(m.group())
            sub = re.sub(pattern, repl, line)
            return sub

        def seperate_tables1(self, table_lines):
            '''
            Seperate each table of table type 1 (they contain '+' in the text) into its own item in tables_text
            '''
            tables_text, current_table = [], []
            plus_ct = line_i = 0
            is_single_col = False
            for table_line in table_lines:
                for line in table_line:
                    #if header line
                    if line_i == 1:
                        line = self.replace_invalid_char_header(line)
                    if line.count('+') == 2:
                        is_single_col = True
                    if '+-' in line:
                        plus_ct += 1

                    if is_single_col:
                        line = self.add_filler_col1(line_i, line, plus_ct == 3)
                    current_table.append(line)
                    line_i += 1
                    if plus_ct == 3:
                        tables_text.append('\n'.join(current_table))
                        current_table = []
                        is_single_col = False
                        plus_ct = line_i = 0
            return tables_text

        def seperate_tables2(self, table_lines):
            '''
            Seperate each table of table type 2 (they contain '|' in the first line) into its own item in tables_text list
            '''
            tables_text, current_table = [], []
            for table_line in table_lines:
                is_single_col = False
                if table_line[0].count('|') == 2:
                    is_single_col = True
                for line_i, line in enumerate(table_line):
                    if line_i == 0:
                        line = self.replace_invalid_char_header(line)
                    if is_single_col:
                        line = self.add_filler_col2(line_i, line)
                    current_table.append(line)
                tables_text.append('\n'.join(current_table))
                current_table = []
            return tables_text

        def add_result_tbl_name(self, names):
            if 'Result' not in names and 'result' not in names:
                names.append('Result')
            return names

        def get_closest_names(self,  target_len, names_args):
            '''
            Returns the names list that has a length closest to the number of tables parsed
            '''
            min_diff = float('inf')
            for names in names_args:
                diff = abs(target_len - len(names))
                if diff < min_diff:
                    min_diff = diff
                    names_final = names

            if min_diff == 0:
                return names_final
            elif len(names_final) > target_len:
                print('CAUTION: Unknown table nams- too many names parsed compared to # of tables')
                while len(names_final) != target_len:
                    names_final.pop()
            else:
                i = 0
                print('CAUTION: Unknown table names- too few names parsed compared to # of tables')
                while len(names_final) != target_len:
                    names_final.append('Unknown{i}'.format(i=i))
                    i+=1
            return names_final

        def parse_table_names(self, tables_pre, target_len):
            #1 This method gets tables using regex looking for keyword 'table'
            pattern = re.compile('.+table')
            names_kword = pattern.findall(''.join(tables_pre))
            names_kword = [table_name.replace('table','').strip() for table_name in names_kword]
            names_kword = self.add_result_tbl_name(names_kword)
            if len(names_kword) == target_len:
                return names_kword

            #method 2, from <pre> tag, collects the first word above each table line
            table_pre = '\n'.join(tables_pre)
            try:
                #capture words before first table
                name_first = [re.match(r'(.*)\n\+-', table_pre).group(1)]
                #capture words between 2 new lines, and next table
                names_remaining = re.findall(r'\n\n(.*?)\n\+-', table_pre)
                names_positional = name_first + names_remaining
                names_positional = [name.split()[0] for name in names_positional]
                if len(names_positional) == target_len:
                    return names_positional
            except (AttributeError, IndexError):
                names_positional = []

            #3 This method gets table names using <code> tag, i.e. #176
            elements = self.driver.find_elements_by_css_selector("code")
            element_names = set([element.text for element in elements])
            pattern = re.compile(r'[a-zA-Z]+')
            invalid_names = ['null', 'DIAB1']
            names_code = []
            for name in element_names:
                if pattern.match(name) and name not in invalid_names:
                    names_code.append(name)
            names_code = self.add_result_tbl_name(names_code)
            if len(names_code) == target_len:
                return names_code

            return self.get_closest_names(target_len, [names_kword, names_positional, names_code])

        def parse_leetcode_tables(self, leet_win):
            '''
            The main parsing function that combines everything together. The tables are always listed under the <pre> tag. Tables_pre includes alll this text. However, it also includes extraneous text. Table_lines removes the extraneous text. Lastly, each of the tables are seperated as an item
            '''
            self.driver.switch_to_window(leet_win)
            tables_pre = self.parse_table_pre()
            table_lines = self.parse_table_lines(tables_pre)

            #seperate tables based on type
            if self.is_table1(table_lines):
                tables_text = self.seperate_tables1(table_lines)
            else:
                tables_text = self.seperate_tables2(table_lines)
                
            table_names = self.parse_table_names(tables_pre, len(tables_text))
            return table_names, tables_text

    def open_db_win(self, url='https://www.db-fiddle.com/'):
        self.db_win = self.open_new_win(url)

    def db_fiddle_select_engine(self):
        self.driver.switch_to_window(self.db_win)
        WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.element_to_be_clickable((By.CLASS_NAME, 'ember-power-select-status-icon'))).click()
        try:
            self.driver.find_elements_by_class_name('ember-power-select-option')[config_db_fiddle.DB_ENGINE].click()
        except IndexError:
            print('\nInvalid sql engine selection, changing to mySQL8')
            self.driver.find_elements_by_class_name('ember-power-select-option')[0].click()

    def db_fiddle_query_input(self, table_name):
        self.driver.switch_to_window(self.db_win)
        #Code Mirror lines element must be activated, before textbox element can be sent keys
        code_mirror = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="query"]/div[2]/div[6]/div[1]/div/div/div')))
        code_mirror.click()
        textbox = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.presence_of_element_located((By.XPATH, '//*[@id="query"]/div[2]/div[1]/textarea')))
        query = 'SELECT * FROM {table_name}'.format(table_name=table_name)
        textbox.send_keys(query)

    def db_fiddle_table_input(self, table_name, table_text):
        self.driver.switch_to_window(self.db_win)
        fluent_wait = WebDriverWait(self.driver, self.__WAIT_SHORT, poll_frequency=.5, ignored_exceptions=[ElementNotVisibleException, ElementNotSelectableException])
        fluent_wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="schema"]/div[3]/button[1]'))).click()
        table_name_input = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.presence_of_element_located((By.XPATH, "//div[@id='textToDDLModal']//*[starts-with(@class,'modal-body')]//*[starts-with(@id,'ember')]/input")))
        table_name_input.send_keys(table_name)

        table_input = fluent_wait.until(EC.presence_of_element_located((By.XPATH, "//div[@id='textToDDLModal']//*[starts-with(@class,'modal-body')]//*[starts-with(@id,'ember')]/textarea")))
        table_input.send_keys(table_text)
        append_button = WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.element_to_be_clickable((By.XPATH, "//div[@id='textToDDLModal']//*[starts-with(@class,'modal-body')]/button[2]")))
        append_button.click()

    def db_fiddle_save(self):
        self.driver.switch_to_window(self.db_win)
        pre_url = self.driver.current_url
        try:
            WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="saveButton"]'))).click()
        except:
            WebDriverWait(self.driver, self.__WAIT_SHORT).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="runButton"]'))).click()
        #after saving, wait until url has changed to return the saved url
        WebDriverWait(self.driver, self.__WAIT_LONG).until_not(EC.url_to_be(pre_url))
        return self.driver.current_url

    def close_question(self):
        if len(self.driver.window_handles) == 0:
            raise NoSuchWindowException
        end_url = None
        try:
            self.driver.switch_to_window(self.db_win)
            if config_db_fiddle.SAVE_BEFORE_CLOSING:
                end_url = self.db_fiddle_save()
            else:
                end_url = self.driver.current_url
        except:
            pass
        self.close_question_windows()
        return end_url

    def open_question(self, q_num, db_prev_url=None):
        '''
        Opens the leetcode problem, and a db-fiddle of that problem
        '''
        self.open_leetcode_win(q_num)

        #a db fiddle has already been created
        if db_prev_url is not None and self.is_valid_save_url(db_prev_url):
            if config_db_fiddle.CHECK_NEW_SAVE_VERSIONS:
                db_start_url = self.open_newest_fiddle_url(db_prev_url)
            else:
                db_start_url = db_prev_url
                self.open_db_win(db_start_url)

        #no db-fiddle has been created yet
        else:
            self.open_db_win()
            self.db_fiddle_select_engine()
            try:
                #parse the sql tables from leetcode.jp
                table_names, tables_text = self.TableParser(self.driver).parse_leetcode_tables(self.leet_win)
            #couldn't find sql tables to parse
            except (NoSuchElementException, IndexError) as e:
                return None
            #dump parsed tables onto db fiddle
            for i, table_text in enumerate(tables_text):
                self.db_fiddle_table_input(table_names[i], table_text)
            self.db_fiddle_query_input(table_names[0])
            db_start_url = self.db_fiddle_save()
        self.driver.switch_to_window(self.leet_win)
        return db_start_url
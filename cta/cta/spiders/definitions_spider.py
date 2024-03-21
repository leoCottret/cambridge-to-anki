import scrapy
from ..items import ScrapyAnkiCambridgeItem
import subprocess
import os
from dotenv import load_dotenv
from typing import List

from collections import Counter
from pathlib import Path

# Quote Spider
class QS(scrapy.Spider):
    load_dotenv() # load env variables

    N = 'None' # to avoid mypy errors
    name = 'definitions'
    BASE_DOMAIN = 'https://dictionary.cambridge.org'
    BASE_URL = BASE_DOMAIN + '/dictionary/english/'

    # cf .env file for explanations
    WORD_LIST_FILE_PATH: str = os.getenv('WORD_LIST_FILE_PATH', N)
    WORD_LIST_FILE_BACKUP_PATH: str = os.getenv('WORD_LIST_FILE_BACKUP_PATH', N)
    ANKI_MEDIA_FOLDER_PATH: str = os.getenv('ANKI_MEDIA_FOLDER_PATH', N)
    ANKI_FILE_FLAG: str = os.getenv('ANKI_FILE_FLAG', N)
    ANKI_IMPORT_NOTE_ID_FLAG: str = os.getenv('ANKI_IMPORT_NOTE_ID_FLAG', N)
    CUSTOM_USER_AGENT: str = os.getenv('CUSTOM_USER_AGENT', N)
    VERSION: str = os.getenv('VERSION', N)

    if WORD_LIST_FILE_PATH == N or WORD_LIST_FILE_BACKUP_PATH == N or ANKI_MEDIA_FOLDER_PATH == N or CUSTOM_USER_AGENT == N or WORD_LIST_FILE_BACKUP_PATH == N or ANKI_FILE_FLAG == N or ANKI_IMPORT_NOTE_ID_FLAG == N or VERSION == N:
        print('ERROR: One of the .env variable is missing, did you copy the file correctly?')
        exit()


    WTF: List[str] = [] # words to filter, eg: 'praised' word -> filter on 'prais'

    # load back up list
    backup_list: List[str] = []
    with open(WORD_LIST_FILE_BACKUP_PATH, 'r', encoding='UTF-8') as file:
        while line := file.readline():
            backup_list.append(line.rstrip())
    backup_list.sort()

    # rewrite back up file with alphabetical order, convenient
    with open(WORD_LIST_FILE_BACKUP_PATH, 'w', encoding='UTF-8') as file:
        for word in backup_list:
            file.write(word + '\n')

    # load wordlist from file
    start_urls: List[str] = []
    request_words: List[str] = []
    with open(WORD_LIST_FILE_PATH, 'r', encoding='UTF-8') as file:
        while line := file.readline():
            word = line.rstrip()
            request_words.append(word)
            start_urls.append(BASE_URL + word)
    
    # rewrite word list file with alphabetical order, without blacklisted words, convenient
    request_words = [k for k,v in Counter(request_words).items() if v==1]
    request_words.sort()

    with open(WORD_LIST_FILE_PATH, 'w', encoding='UTF-8') as file:
        for word in request_words:
            file.write(word + '\n')

    # --- FUNCTIONS ---
    # execute os command and check if it has been executed sucessfully
    # if not, print why and crash the stop the script (it should NOT happen)
    def execute_command(os_command: str):
        p = subprocess.Popen(os_command, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate() # (stdout, stderr)
        # wait for command to finish
        p_status = p.wait()

        # 0 = command succeeded
        if p_status != 0:
            print('OS command error! command -> '+ str(os_command) + '\tstderr -> ' + str(err) +  "\tstdout -> " + str(output))
            exit()
    # the right delimiters that defines that a word end here -> "someWord," <- comma, the word ends here
    @staticmethod
    def RIGHT_DELIMITERS() -> List[str]:
        return [' ', ',', '.', ':', '!', '?', '/', '\'', ')']
    @staticmethod
    def LEFT_DELIMITERS() -> List[str]:
        return [' ', '/', '\'', '('] # while ':' is not a LEFT_DELIMITERS, we can't create a closure in a closure by mistake
    
    # create an anki closure for this word eg slender -> s{{c1::lender}}
    # PS: could be improved to create c2, c3 etc. with an extra parameter, but it doesn't make much sense for word cards
    def getAnkiClosure(word: str, limit: int =1) -> str:
        return word[:limit] + '{'+ '{' + 'c1::' + word[limit:] + '}' + '}'

    # check if the text contains a word to filter. Check for a word, not the part of an other word
    # eg1: WTF -> 'man', txt -> 'The phones are manned, 24 hours a day.'
    # res1: returns false, manned is ignored despite containg man
    # eg2: WTF -> 'man', txt -> 'Man! It's so hot!'
    # res2: returns true, man is taken into account despite having M as uppercase, and having a "!" next to it
    # TLDR: I didn't use an already made function because my needs were quite specific
    def doesTextContainsWordsToFilter(txt: str) -> bool:
        for w in QS.WTF:
            ctn = 0
            w_l = len(w)
            while ctn <= len(txt)-w_l:
                if txt[ctn:ctn+w_l].lower() == w:
                    # CF createClosures
                    if (ctn == 0 or any(txt[ctn-1] in x for x in QS.LEFT_DELIMITERS())): # TODO remove dead code  # and (ctn+w_l>=len(txt) or any(txt[ctn+w_l] in x for x in QS.RIGHT_DELIMITERS())):
                        return True
                ctn += 1
        return False

    def createClosures(txt: str) -> str:
        for w in QS.WTF:
            ctn = 0
            w_l = len(w)
            while ctn <= len(txt)-w_l:
                if txt[ctn:ctn+w_l].lower() == w:
                    # TODO verifying that we're not in a closure already eg m{{c1::an}} -> then check or 'an' ->m{{c1::{{c1::an}}}}
                    # PS: IMPORTANT --> while ':' is not a LEFT_DELIMITERS, we can't create a closure inside a closure by mistake
                    # PPS: I removed the right delimiter to hopefully better hide the words, eg: man -> woman (no, 'o' isn't left delimiter), manned -> m{{c1::an}}ned, space is a left delimiter
                    if (ctn == 0 or any(txt[ctn-1] in x for x in QS.LEFT_DELIMITERS())): # TODO remove dead code # and (ctn+w_l>=len(txt) or any(txt[ctn+w_l] in x for x in QS.RIGHT_DELIMITERS()))
                        txt = txt[:ctn] + QS.getAnkiClosure(txt[ctn:ctn+w_l]) + txt[ctn+w_l:]
                        ctn += 8 # {{c1::}} -> 8 characters
                ctn += 1
        return txt
    
    def getText(parent, selector, add_left: str = '', add_right: str = '', closure: bool = True) -> str:
        word = parent.css(selector).extract()
        wordStr: str = ''
        for i in range(len(word)):
            txt: str = word[i].replace('\n', '')
            while len(txt) > 0 and txt[0] == ' ':
                txt = txt[1:]
            while len(txt) > 0 and txt[len(txt)-1] == ' ':
                txt = txt[:-1]
            if i == 0:
                wordStr += txt
            else:
                # to avoid eg man noun ( MALE ), so last character of the word before must not be a bracket
                # and first character of current word must not be a )
                if (len(txt) > 0 and len(wordStr) > 0 
                    and not any(txt[0] in x for x in QS.RIGHT_DELIMITERS()) 
                    and not any(wordStr[len(wordStr)-1] in x for x in QS.LEFT_DELIMITERS())):
                    wordStr += ' ' + txt
                else:
                    wordStr += txt

        if closure:
            wordStr = QS.createClosures(wordStr)

        if wordStr != '' and wordStr != ' ':
            wordStr = add_left + wordStr + add_right
        
        return f"{wordStr}" if wordStr else ''

    #  --- MAIN ---
    def parse(self, response):
        if str(response.request.url) == QS.BASE_URL:
            # TODO implement tracking of words and a final function execution to know which words have been skipped
            print('ERROR: a word does not exist! Search for 302 in cambridgetoanki.log to find which one')
            return

        items = ScrapyAnkiCambridgeItem()
        url_split = str(response.url).split('/')
        title = url_split[len(url_split)-1] # to rename the audio file
        title = title.split('?')[0] # remove part before ? if it exists, it's just a redirection

        # replace weird special characters that can be found in url on some rare occasions by '_', to avoid naming the images and audio files with uncommon characters
        for i in range(len(title)):
            if not title[i].isalnum():
                title = title[:i] + '-' + title[i+1:]

        # DO NOT REMOVE
        print(title)
        note_id = QS.ANKI_IMPORT_NOTE_ID_FLAG + '-' + title
        front = '<!-- ' + QS.ANKI_FILE_FLAG + ' ' + QS.VERSION  + ' -->\n' # front of the anki card
        back = '' # back of the anki card

        check_valid_word = response.css('.di-body')
        if len(check_valid_word) > 0:
            # check if it's a present participle of an other word, in that case use this word instead
            check_redirection_pp = check_valid_word[0].css(".entry-body")[0].css(".entry-body__el")[0].css('.usage.dusage::text')
            if len(check_redirection_pp) > 0:
                check_redirection_pp = check_redirection_pp[0].extract()
            else:
                # eg mold -> mould (we want the UK version)
                check_redirection_pp = check_valid_word[0].css(".entry-body")[0].css(".entry-body__el")[0].css('.def-block')
                if len(check_redirection_pp) > 0:
                    check_redirection_pp = QS.getText(check_redirection_pp[0], '.def *::text', '', '', False)

            # present participle of an other word, follow the redirection and create a card for this word instead
            # the reason being, like most dictionnaries it won't have definitions but just a redirection to it, so it creates an almost empty card
            #   same for past simple, past participle, and both at once
            #   same for US spelling of 
            if check_redirection_pp == 'present participle of' or check_redirection_pp == 'past simple of' or check_redirection_pp == 'past participle of' or check_redirection_pp == 'past simple and past participle of' or (len(check_redirection_pp)>14 and check_redirection_pp[:14] == 'US spelling of'):
                print('redirection: ' + str(response.url))
                new_word = response.css(".di-body")[0].css(".entry-body")[0].css(".entry-body__el")[0].css('.def')[0].css('.Ref *::text')[0].extract()
                print('NEW WORD ' + new_word)

                yield response.follow(QS.BASE_URL + new_word)
                return
        else:
            # the word is not valid, it doesn't exist in this dictionnary (should be catched)
            print('ERROR: this should never happen: ' + str(response.url) + ' ' + 'doesn\'t have a di-body class')
            return


        parent = response.css('.di-body')[0].css('.entry-body')[0] # every definitions
        # main definitions = with different types eg man:noun, man:verb, man:exclamation
        definitions = parent.css('.entry-body__el')
        counter = 0
        img_counter = 0 # we need an extra counter to avoid overwriting the same image when we download it

        for definition in definitions:
            counter += 1
            # HEADER --> type, pronunciations
            # response.css(".di-body")[0].css(".entry-body")[0].css(".entry-body__el")[0].css('.pos-header').extract()
            header = definition.css('.pos-header')

            QS.WTF = []
            word = QS.getText(definition, '.di-title *::text')
            
            type = QS.getText(header, '.posgram>span::text')
            # "> * ::text" -> text in every child recursively
            # "> *::text" -> text in every direct child
            type_extra = QS.getText(header, '.posgram>.gram> * ::text')
            # PS: there are several kind of source audio, I'll go with the one for HTML5 and .mp3
            # AUDIO --> .mp3 file
            pronunciation_rows = header.css('.uk.dpron-i')
            audio_tag = ''
            if len(pronunciation_rows)>0:
                audio_uk = pronunciation_rows[0].css('audio > source')[0].xpath("@src")[0].extract()
                # 1 audio is enough
                if counter == 1:
                    # download audio file and put it in anki folder
                    # PS: I'm using curl since it works "as is" to download a file via https
                    audio_file_name = QS.ANKI_FILE_FLAG + '_' + title + '.mp3'
                    audio_file_full_path = QS.ANKI_MEDIA_FOLDER_PATH + audio_file_name
                    # check if mp3 file isn't already downloaded
                    check_file_already_downloaded = Path(audio_file_full_path)
                    if not check_file_already_downloaded.is_file():
                        QS.execute_command('curl "' + QS.BASE_DOMAIN + audio_uk + '" -o "' + audio_file_full_path + '" -H "User-Agent: ' + QS.CUSTOM_USER_AGENT + '"')
                    audio_tag += ' [sound:' + audio_file_name + ']'
            else:
                # as fallback, get the american pronunciation instead
                pronunciation_rows = header.css('.us.dpron-i')
                audio_us = pronunciation_rows[0].css('audio > source')[0].xpath("@src")[0].extract()
                # 1 audio is enough
                if counter == 1:
                    # download audio file and put it in anki folder
                    # PS: I'm using curl since it works "as is" to download a file via https
                    audio_file_name = QS.ANKI_FILE_FLAG + '_' + title + '.mp3'
                    audio_file_full_path = QS.ANKI_MEDIA_FOLDER_PATH + audio_file_name
                    # check if mp3 file isn't already downloaded
                    check_file_already_downloaded = Path(audio_file_full_path)
                    if not check_file_already_downloaded.is_file():
                        QS.execute_command('curl "' + QS.BASE_DOMAIN + audio_us + '" -o "' + audio_file_full_path + '" -H "User-Agent: ' + QS.CUSTOM_USER_AGENT + '"')
                    audio_tag += ' US: [sound:' + audio_file_name + ']'


            # get the plural/conjugations, used to create closures in the card. Is optional
            words_extra = header.css('.inf.dinf::text').extract()

            # set the words to lowercase
            word_wtf_split = word.split()
            word_wtf = word.lower() if len(word_wtf_split) == 1 else word_wtf_split[0].lower()
            # "upshot" -> res "the upshot", we want "upshot", not "the"!
            if word_wtf == 'the' and len(word_wtf_split) > 1:
                word_wtf = word_wtf_split[1].lower()
            # eg boggle -> boggl, to hide boggling
            # TODO: add smarter checks
            #   eg: ily AND type is adverb (to avoid catching family)
            if word_wtf[len(word_wtf)-1] == 'e' and word_wtf[len(word_wtf)-2] != 'ee':
                word_wtf = word_wtf[:-1]
            elif word_wtf[len(word_wtf)-2:] == 'ed': # eg wrinkled -> hide wrinkle
                word_wtf = word_wtf[:-2]
            elif (word_wtf[len(word_wtf)-3:] == 'ion' or word_wtf[len(word_wtf)-3:] == 'ily') and len(word_wtf) > 6: # eg conjugation -> hide conjugate
                word_wtf = word_wtf[:-3]
            elif (word_wtf[len(word_wtf)-1:] == 'y') and len(word_wtf) > 6: # eg deficiency -> hide deficiencies
                word_wtf = word_wtf[:-1]
            
            
            # (part in Counter()) eg "allude to someone/something" -> "allude", get the first word as word to filter
            #   and remove duplicates
            tmp = [k for k,v in Counter([w for w in QS.WTF] +  [word_wtf] + [s.lower() for s in words_extra]).items()]

            # sort the list, longest word first because we'll prefer to hide the longest word in priority (eg meant>mean)
            tmp.sort()
            # set words that we need to create closures for
            QS.WTF = tmp
            front += '<h4>' + str(counter) + '. ' + QS.getAnkiClosure(word + (audio_tag if audio_tag != '' else ''))  + ' ' + type + ' ' + type_extra + '</h4>\n'
            

            # extra stuff is extra convoluted but there are many possible cases
            extra_stuff = QS.getText(header, '.anc-info-head *::text', '', '') # eg phrasal verb
            extra_stuff_2 = QS.getText(definition, '.di-info>.lab *::text, .pos-header>.lab *::text', '', '') # eg formal, disapproving
            extra_stuff_3 = QS.getText(header, '.spellvar *::text, .dspellvar *::text', '', '') # eg anticonvulsant, also anti-convulsant, old-fashioned
            
            extra_title = extra_stuff_3.split('also ')
            if ( len(extra_title) > 1 ):
                QS.WTF.append(extra_title[1].split(')')[0])
            
            extra_final = extra_stuff
            extra_final += ((', ' + extra_stuff_2) if extra_final.isspace() else extra_stuff_2)
            extra_final += ((', ' + extra_stuff_3) if extra_final.isspace() else extra_stuff_3)
            extra_final = (('<i><div>' + extra_final + '</i></div>\n') if not extra_final.isspace() else '')
            front += extra_final
            
            # add plural, present participle etc.
            if len(words_extra) > 0:
                group = header.css('.inf-group *::text')
                if len(group) > 0:
                    group = group.extract() # TODO unused??
                    # PS: `.stuff::text, .stuff> *::text` -> text in .stuff AND every direct child
                    txt = QS.getText(header, '.inf-group::text, .inf-group> *::text', '<div><i>', '</i></div>\n<br>')
                    front += txt
                else:
                    for word_extra in words_extra:
                        front += '<i>' + QS.createClosures(word_extra) + '</i>\n'
                    front += '\n'
            # BODY
            subdefinitions = definition.css('.dsense')
            subcounter = 96 # ASCII code, to get eg 'a', 'b' etc.
            for subdefinition in subdefinitions:
                subcounter += 1
                category = QS.getText(subdefinition, 'h3 * ::text', '<h5>' + str(counter) + chr(subcounter)+'. ', '</h5>')
                front += category + '\n'
                # <=> subsubdefinitions...
                # Don't mind those commented piece of codes, they are just very useful to debug in shell mode
                # response.css(".di-body")[0].css(".entry-body")[0].css(".entry-body__el")[0].css('.dsense')[0].css('.def-block').extract()
                def_blocks = subdefinition.css('.def-block')
                for def_block in def_blocks:
                    def_info = QS.getText(def_block, '.def-info *::text', '<i>', '</i>')
                    
                    # a picture is worth a thousand words
                    def_img =  def_block.css('amp-img')
                    if len(def_img) > 0:
                        img_counter += 1
                        # response.css(".di-body")[0].css(".entry-body")[0].css(".entry-body__el")[1].css('.dsense')[0].css('.def-block').css('amp-img')[0].xpath('@on')[0].extract()
                        def_img_src = def_img.xpath('@on')[0].extract()
                        def_img_src = def_img_src.split('src: \'')[1].split('\' }')[0]
                        def_img_src = QS.BASE_DOMAIN + def_img_src
                        
                        # PS: I'm using curl since it works "as is" to download a file via https
                        def_img_file_name = QS.ANKI_FILE_FLAG + '_' + title + '_' + str(counter) + '_' + str(img_counter) + '.jpg'
                        def_img_file_full_path = QS.ANKI_MEDIA_FOLDER_PATH + def_img_file_name
                        # check if audio file isn't already downloaded NOT USED
                        check_file_already_downloaded = Path(def_img_file_full_path)
                        if not check_file_already_downloaded.is_file():
                            # TODO import the logging library and implement it
                            # TODO add debug logging for all the OS commands
                            QS.execute_command('curl ' + def_img_src + ' -o "' + def_img_file_full_path + '" -H "User-Agent: ' + QS.CUSTOM_USER_AGENT + '"')
                        def_img_tag = "<img src='" + def_img_file_name + "' width='400px'>" #  style='filter: invert(1)'>"
                        front += def_img_tag
                    
                    def_block_def = QS.getText(def_block, '.def *::text')
                    front += '<div>' + def_info + ' ' + def_block_def + '</div>\n'
                
                    examples = def_block.css('.examp')
                    for i in range(len(examples)):
                        # we absolutly want an example with a word that we know we can filter
                        # if we cannot find one, it's probably a slight variation that won't be filtered
                        # eg: man -> manned. In that case, we ignore the example
                        # we also want only 1 valid example to avoid having too much text
                        if QS.doesTextContainsWordsToFilter(QS.getText(examples[i], '::text', '', '', False)):
                            front += QS.getText(examples[i], '::text', '<div>&emsp;&ensp;<i>', '</i></div>\n')
                            # if we have too many def_blocks, it's best to only get one example. Otherwise, they are a welcomed addition
                            # example: if we have 2 def_blocks, we can go up to 3 examples for them
                            if i > 3 - len(definitions) - len(def_blocks):
                                break
                    front += '<hr>\n'
        
        # populate the items variable (<=> a new card) and we're done!
        # PS: since the columns are sorted in alphabetical, I renamed the field like that for conveniency
        #   the clean way would be to sort all the items before the CSV export, eg: https://docs.scrapy.org/en/latest/topics/exporters.html
        items['anote_id'] = note_id
        items['front'] = front
        items['zback'] = back
        yield items # returns a dictionnary
#!/usr/bin/env python3
# coding: utf-8

# ### Post Edited Text

import re
from dateutil.parser import parse
import xmltodict
from collections import namedtuple
from collections import OrderedDict
import logging
# Set the logging basic level = INFO
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)
# Record format for Translog
Record = namedtuple('Record',['source', 'targetUpdated', 'captured_keystrokes','last_timestamp', 'mt_output'])

def processTradosFile(xmlDoc, recordNumber=None, debug=False):
    
    # Keeps track if the task is Translation or Post-editing
    task = "translating"
    mt_output_counts = 0
    duplicate_records = 0
    
    # Stores the keystores for each segment in a dictionary
    recorded_keystrokes_dict = dict()
    #source_record_id_dict = {}
    #segment_record_id_dict = {}

    started_time = xmlDoc['QualitivityProfessional']['Client']['Project']['Activity']['@started']
    end_time = xmlDoc['QualitivityProfessional']['Client']['Project']['Activity']['@stopped']
    source_lang = xmlDoc['QualitivityProfessional']['Client']['Project']['Activity']['Document']['@sourceLang']
    if source_lang:
        source_lang = source_lang.split('-')[0]
    target_lang = xmlDoc['QualitivityProfessional']['Client']['Project']['Activity']['Document']['@targetLang']
    if target_lang:
        target_lang = target_lang.split('-')[0]
    #print(target_lang, source_lang)
    project_name = xmlDoc['QualitivityProfessional']['Client']['Project']['@name']

    # To store the timestamp of the first keystroke of the first ever record
    first_timestamp = 0.0
    # To store the timestamp of last keystroke of previous record
    last_timestamp = 0.0
    records = xmlDoc['QualitivityProfessional']['Client']['Project']['Activity']['Document']['Record']
    #recoveredText = ''
    # To extract details for a single record
    if recordNumber:
        for record in records:
            #record = records[record_number]
            recordId = int(record['@id'])
            segmentId = int(record['@segmentId'])
            if recordId == recordNumber:
                targetUpdated = removeHTMLtags(record['contentText']['targetUpdated'])
                # For some records, the field targetUpdated is absent
                # We assume this record as "not translated"
                if not targetUpdated:
                    print(f"[WARN] No targetUpdated found!!")
                    return

                capturedData, first_timestamp = processRecord(record, first_timestamp, last_timestamp, debug)
                recorded_keystrokes_dict[segmentId] = capturedData
                break
        print(f"[INFO] targetUpdated: '{targetUpdated}'",end='\n\n')


    # To extract the whole trados xml file
    else:
        
        for ind, record in enumerate(records):
            #sourceText = record['contentText']['source']
            targetUpdated = record['contentText']['targetUpdated']
            recordId = int(record['@id'])
            segmentId = int(record['@segmentId'])
            
            # For some records, the field targetUpdated is absent
            # We assume this record as "not translated"
            # We skip this record
            if not targetUpdated:
                print(f"[WARN] No targetUpdated found for Record Id: {recordId}!!")
                continue

            capturedData, first_timestamp = processRecord(record, first_timestamp, last_timestamp, debug)
            last_timestamp = capturedData.last_timestamp
            
            if capturedData.mt_output : 
                mt_output_counts += 1
            
            # Check for duplicate record ids
            if segmentId in recorded_keystrokes_dict.keys():
                duplicate_records +=1
                #previousSegmentId = segment_record_id_dict[segmentId]
                previousCapturedData = recorded_keystrokes_dict[segmentId]
                #previousCapturedData.last_timestamp = capturedData.last_timestamp
                # append the keystrokes
                new_captured_keystrokes = previousCapturedData.captured_keystrokes + capturedData.captured_keystrokes
                # update the last_timestamp and targetUpdated
                recorded_keystrokes_dict[segmentId] = Record(capturedData.source, capturedData.targetUpdated, new_captured_keystrokes, capturedData.last_timestamp, previousCapturedData.mt_output)
                if debug:
                    print(f"[WARN] Record ID {recordId} updates existing segment {segmentId}")
            else:
                #segment_record_id_dict[sourceText] = recordId
                recorded_keystrokes_dict[segmentId] = capturedData
        
    if mt_output_counts:
        task = "PE"
        
    print(f"[WARN] Total Number of duplicate records = {duplicate_records}")
    print(f"[INFO] Total Number of processed records = {len(recorded_keystrokes_dict.keys())}")
    
    return recorded_keystrokes_dict, started_time, end_time, source_lang, target_lang, project_name, task

def convertTimestampToMs(ts):
    
     tt = parse(ts)
     tt = tt.timestamp()
     tt = int(tt * 1000)
     return tt
"""
def removeHTMLtags(text, debug=False):
    count = 0
    while(re.findall(r'<(\w+)\s+.+?>(.*?)</\1>', text)):
        count +=1
        if debug:
            print(f"[DEBUG] Iteration: {count}")
        text = re.sub(r'<(\w+)\s+.+?>(.*?)</\1>', '\\2', text)
        text = re.sub(r'\xa0',' ',text)
    if not count and debug:
        print("[INFO] No html tags found")
    return text
"""

def removeHTMLtags(text, debug=False):
    
    if text and re.findall(r'</?.*?>', text) :
        text = re.sub(r'</?.*?>', '', text)
        text = re.sub(r'\xa0',' ',text)
    return text


def processRecord(record, first_timestamp, last_timestamp, debug=False):
    """
    This method processes each segment(record) of Trados Post Editing XML file
    """
    # Stores the list of keystrokes
    captured_keystrokes = []
    # Stores the output generated by MT systems in case of Post Editing Tasks
    mt_output = ''

    ts = 0.0
    #last_ts = 0.0
    recordId = record['@id']
    segmentId = record['@segmentId']
    source = removeHTMLtags(record['contentText']['source'])
    targetOriginal = removeHTMLtags(record['contentText']['targetOriginal'])
    targetUpdated = removeHTMLtags(record['contentText']['targetUpdated'])
    
    recordStoppedTs = record['@stopped']
    recordStoppedTs = convertTimestampToMs(recordStoppedTs)
    recordStartedTs = record['@started']
    recordStartedTs = convertTimestampToMs(recordStartedTs)
    
    # All the timestamps are calculated as difference in ms from  timestamp of very first record of the document
    if first_timestamp == 0.0:
        first_timestamp = recordStartedTs
    else:
        recordStartedTs = recordStartedTs - first_timestamp
        recordStoppedTs = recordStoppedTs - first_timestamp
    
    # some records doesn't have any keyStrokes that is <keyStrokes/>
    if not record['keyStrokes']:
        print(f"[INFO] No Keystrokes for Record Id: {recordId} and Segment Id: {segmentId}")
        return Record(source, targetUpdated, captured_keystrokes, recordStoppedTs, mt_output), first_timestamp
    
    keystrokes = record['keyStrokes']['ks']
    
    if targetOriginal:
        original_text = targetOriginal
    else:
        original_text = ''

    for ks in keystrokes:
        # In some cases, the keystrokes only has 1 record
        # In that case, return the text field as the translated text
        if isinstance(ks,str):
            print(f"[INFO] No keystrokes only MT Output for Record Id: {recordId} and Segment Id: {segmentId}")
            return Record(source, targetUpdated, captured_keystrokes, recordStoppedTs, removeHTMLtags(keystrokes['@text'])), first_timestamp

        system = ks.get('@system')
        # The system attribute contains the MT translation
        # Fetch that text and use it at initial original_text
        if system:
            original_text = ks.get('@text')
            mt_output = ks.get('@text')
            break

    if debug: print(f"[INFO] Target Original Text: '{original_text}'")

    # Convert the target original_text to array of characters
    orig_text = [w for w in original_text]

    # Assign the first_timestamp to the last_timestamp recorded of the last record

    for ks in keystrokes:
        text = removeHTMLtags(ks.get('@text'))
        key = ks.get('@key')
        position = ks.get('@position')
        pos = int(position)
        created = ks.get('@created')
        selection = removeHTMLtags(ks.get('@selection'))
        system = ks.get('@system')

        if system:
            continue

        # Timestamp calculation from unix timestamp to time in miliseconds
        #tt = parse(created)
        #tt = tt.timestamp()
        tt = convertTimestampToMs(created)

        #if first_timestamp == 0.0:
         #   first_timestamp = tt
        ts = tt - first_timestamp
        # convert tt into miliseconds
        #ts = int(ts*1000)
        #last_ts = ts
        #print(f"record ID: {recordId}, pos: {pos}, timestamp: {ts}")
        # Skip this keystroke as it contains the MT translation and is taken care of earlier
        if system:
            continue
        # If the keystroke has non empty "selection" attribute
        if selection:
            if debug:
                print(f"[DEBUG] Select and delete Characters")

            orig_text, ks_list = extractSelectionKeystrokesPE(orig_text, selection, pos, text, key, ts, debug)
            curr_updated_text = ''.join(orig_text)
            if debug:
                print(f"[DEBUG] Current Updated Text = '{curr_updated_text}'")
            for ks in ks_list:
                captured_keystrokes.append(ks)
        # Keystroke is either Insert or Delete
        else:
            # Stores the type of operation - insert or delete
            #op_type = ''

            # So far this funtionality is not used
            if key == '[BACK]':
                opType = "delete"
                del(orig_text[pos])
                curr_updated_text = ''.join(orig_text)
                if debug:
                    print(f"[DEBUG] Deleting characters at position: {pos}")
                    print(f"[DEBUG] Text after Deletion = '{curr_updated_text}'")

            else:
                opType = "insert"
                for index, char in enumerate(text):
                    orig_text.insert(pos + index, char)
                curr_updated_text = ''.join(orig_text)
                if debug:
                    print(f"[DEBUG] Inserting characters: '{text}' at position: {pos}")
                    print(f"[DEBUG] Text after Insert = '{curr_updated_text}'")

            target_ks = {'Time': str(ts), 'Cursor': position, 'Type': opType, 'Value': text}
            captured_keystrokes.append(target_ks)

    if debug: print(f"[DEBUG] The recovered text: {curr_updated_text}")
     # Validation
    if (targetUpdated == curr_updated_text):
        print(f"[INFO] Success for Record Id: {recordId} and Segment Id: {segmentId}")
    else:
        print(f"[WARN] The recovered text doesn't match targetUpdated for Record Id: {recordId}")
        print(f"\t[ERROR] The recovered text: '{curr_updated_text}'")
        print(f"\t[ERROR] The targetUpd text: '{targetUpdated}'")

    return Record(source, targetUpdated, captured_keystrokes, recordStoppedTs, mt_output), first_timestamp


def extractSelectionKeystrokesPE(orig_text, selection, position, text, key, time, debug):
    ks_list = []
    curr_updated_text = ''.join(orig_text)

    if debug: print(f"[DEBUG] Current Updated Text: '{curr_updated_text}'")

    start = position
    end = position + len(selection)
    #remove_index = [i for i in range(start,end)]

    to_delete = ''.join(orig_text[start:end])
    if debug:
        print(f"\t[DEBUG] To delete at position {position}: character '{orig_text[position]}' text: '{to_delete}'")
        print(f"\t[DEBUG] Selection: '{selection}'")
    if selection != to_delete:
        print(f"\t[ERROR] Selection and to_delete doesn't match at position {position}")

    # Delete characters
    del(orig_text[start:end])

    # Create a keystroke entry for delete
    target_ks = {'Time': str(time), 'Cursor': start, 'Type': "delete", 'Value': selection}
    ks_list.append(target_ks)

    # Insert Space
    if key == '[Space]' and text == ' ':
        orig_text.insert(start,' ')
        # Create a keystroke entry for insert
        target_ks = {'Time': str(time), 'Cursor': start, 'Type': "insert", 'Value': ' '}
        ks_list.append(target_ks)

    else:
        # Insert characters
        if debug:
            print(f"\t[DEBUG] To insert after delete: '{text}'")
        if text:
            for i,c in enumerate(text):
                orig_text.insert(start+i,c)
            # Create a keystroke entry for insert
            target_ks = {'Time': str(time), 'Cursor': start, 'Type': "Insert", 'Value': ' '}
            ks_list.append(target_ks)

    if debug: print(f"[DEBUG] Current updated Text after insertion: '{''.join(orig_text)}'")

    return orig_text, ks_list

def generateTranslogXml(trados_records, started_time, end_time, source_lang, target_lang, project_name, task, target_xml=OrderedDict(), insertLineBreak=True, debug=False):
    if not isinstance(target_xml, OrderedDict):
        print("[ERROR] Enter a valid xml file")
        return

    if not trados_records:
        return

    position = 0
    all_keystrokes = []
    final_source_text = ''
    final_target_text = ''
    final_mt_output = ''
    final_stop_ts = 0
    keys = list(trados_records.keys())
    
    # Sort by segmentId
    keys.sort()
    for recordId in keys:
        record = trados_records.get(recordId)

        sourceText = record.source
        targetText = record.targetUpdated
        mtOutput = record.mt_output
        keystrokes = record.captured_keystrokes
        last_timestamp = record.last_timestamp
        # Capture the value of last_timestamp of last record to be used in <System> tag
        final_stop_ts = last_timestamp
        for ks in keystrokes:
            ks['Cursor'] = str(int(ks['Cursor']) + position)
        if insertLineBreak:
            sourceText += '\n'
            targetText += '\n'
            mtOutput += '\n'
            position += len(targetText)
            linebreak_ks = {'Time': str(last_timestamp), 'Cursor': str(position), 'Type': "Insert", 'Value': '\n'}
            if keystrokes:
                keystrokes += [linebreak_ks]
                position += 1
        final_source_text += sourceText
        final_target_text += targetText
        final_mt_output += mtOutput
        all_keystrokes += keystrokes

    target_xml = addKeystrokes(all_keystrokes, final_stop_ts, target_xml)
    target_xml = addSourceText(final_source_text, target_xml)
    target_xml = addMTTargetText(final_mt_output, target_xml)
    target_xml = addSourceTextChar(final_source_text, target_xml)
    target_xml = addTargetTextChar(final_target_text, target_xml)
    target_xml = addFinalText(final_target_text, target_xml)

    target_xml['LogFile']['startTime'] = started_time
    target_xml['LogFile']['endTime'] = end_time
    target_xml['LogFile']['Project']['FileName'] = project_name
    target_xml['LogFile']['Project']['Description'] = "Qualitivity"
    target_xml['LogFile']['Project']['Languages']['@source'] = source_lang
    target_xml['LogFile']['Project']['Languages']['@target'] = target_lang
    target_xml['LogFile']['Project']['Languages']['@task'] = task

    return target_xml


def addKeystrokes(keystrokes, final_stop_ts, target_xml, debug=False):

    if target_xml.get('LogFile').get('Events'):
        target_xml['LogFile']['Events']['System'] = []
        target_xml['LogFile']['Events']['Key'] = []
    else:
        target_xml['LogFile']['Events'] = OrderedDict()
        target_xml['LogFile']['Events']['System'] = []
        target_xml['LogFile']['Events']['Key'] = []
        
    system = target_xml['LogFile']['Events']['System']
    system.append({'@Time': '0', '@Value': 'START'})    
    system.append({'@Time': final_stop_ts, '@Value': 'STOP'})
    

    keys = target_xml['LogFile']['Events']['Key']
    #keys.append(OrderedDict())
    for ks in keystrokes:
        keys.append(addKsToDict(ks))

    target_xml['LogFile']['Events']['System'] = system
    target_xml['LogFile']['Events']['Key'] = keys

    return target_xml

def addKsToDict(keystrokes_dic):
    new_dict = {'@Value': keystrokes_dic.get('Value'), '@Time': keystrokes_dic.get('Time'), '@Cursor': keystrokes_dic.get('Cursor'), '@Type': keystrokes_dic.get('Type')}
    return OrderedDict(new_dict)

def addSourceText(sourceText, target_xml):
    target_xml['LogFile']['Project']['Interface']['Standard']['Settings']['SourceText'] = sourceText
    return target_xml

def addSourceTextChar(sourceText, target_xml):
    sourceTextChar = []
    target_xml['LogFile']['SourceTextChar']['CharPos'] = []
    for ind, char in enumerate(sourceText):
        sourceTextChar.append(OrderedDict({'@Cursor': str(ind), '@Value': char}))
    target_xml['LogFile']['SourceTextChar']['CharPos'] = sourceTextChar
    return target_xml

def addTargetTextChar(targetText, target_xml):
    targetTextChar = []
    target_xml['LogFile']['FinalTextChar']['CharPos'] = []
    for ind, char in enumerate(targetText):
        targetTextChar.append(OrderedDict({'@Cursor': str(ind), '@Value': char}))
    target_xml['LogFile']['FinalTextChar']['CharPos'] = targetTextChar
    return target_xml

def addMTTargetText(targetText, target_xml):
    target_xml['LogFile']['Project']['Interface']['Standard']['Settings']['TargetText'] = targetText
    return target_xml

def addFinalText(finalText, target_xml):
    target_xml['LogFile']['FinalText'] = finalText
    return target_xml

def main(input_file_path, loglevel="INFO"):
    
   
    logger.info(f"Inside main")
    template_file_path = "translog_template.xml"
    input_file_path = os.path.abspath(input_file_path)
    
    print(f"\n[INFO]The input file path is {input_file_path}")
    
    if not os.path.exists(input_file_path):
        print("[ERROR] Please enter a valid input file path")
        exit(1)
    head, tail = os.path.split(input_file_path)
    output_file_path = head+"/generated_"+tail

    with open(input_file_path, encoding='utf-8') as fd:
        doc = xmltodict.parse(fd.read(),encoding='utf-8')
    

    captured_trados_data, started_time, end_time, source_lang, target_lang, project_name, task = processTradosFile(doc)



    with open(template_file_path, encoding='utf-8') as fd:
        target_xml = xmltodict.parse(fd.read(),encoding='utf-8')



    updated_xml = generateTranslogXml(captured_trados_data, started_time, end_time, source_lang, target_lang, project_name, task, target_xml)
    #updated_xml = xmltodict.unparse(updated_xml)

    #updated_xml = xmltodict.unparse(updated_xml,)
    f = open(output_file_path, 'w', encoding='utf-8')
    
    print(f"\n[INFO]The output file is generated at {output_file_path}")
    #f.write(updated_xml)
    #f.close()

    # uncomment when you want to save to an output file
    #xmltodict.unparse(updated_xml,output=f,pretty=True, short_empty_elements=True)
    
    # fix to call from Flask. needs to return a string object
    updated_xml = xmltodict.unparse(updated_xml,pretty=True, short_empty_elements=True)
    f.close()
    
    return updated_xml
    
def help():
    print(f"Usage: ./Trados2Translog <path_to_input_file> <optional_output_file_path>")
    #exit(1)
    
import sys
import os.path

#main(args)

# Uncomment
"""
if __name__ == '__main__':
    if len(sys.argv) > 2:
        help()
        exit(1)
        
"""  
    
    #input_file_path = "PE_EN-PT_2.xml"
    
    # chineese file
    #input_file_path = "PE_EN-ZH_2.xml"
    #input_file_path = "PE_new.xml"
    #input_file_path = "Translation_EN-PT.xml"
    # Translation
   
    # Uncomment
    #main(sys.argv[1])
    
    
# temporary
#output = main("PE_EN-PT_2.xml")
#print(type(output))
  
    
    



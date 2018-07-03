#-*- coding: utf-8 -*-

import codecs
import json
import re

from docparser import HTMLParser
from utils import TextUtils
from ner import NERTagger


class ZengJianChiRecord(object):
    def __init__(self, shareholderFullName, shareholderShortName, finishDate, sharePrice, shareNum, shareNumAfterChg, sharePcntAfterChg):
        # 股东
        self.shareholderFullName = shareholderFullName
        # 股东
        self.shareholderShortName = shareholderShortName
        # 结束日期
        self.finishDate = finishDate
        # 增减持股价
        self.sharePrice = sharePrice
        # 增减持股数
        self.shareNum = shareNum
        # 增减持变动后股数
        self.shareNumAfterChg = shareNumAfterChg
        # 增减持变动后持股比例
        self.sharePcntAfterChg = sharePcntAfterChg

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False)

    def normalize_finish_date(self, text):
        pattern = re.compile('(\d\d\d\d)[-.年](\d{1,2})[-.月](\d{1,2})日?')
        match = pattern.search(text)
        if match:
            if len(match.groups()) == 3:
                year = int(match.groups()[0])
                month = int(match.groups()[1])
                day = int(match.groups()[2])
                return '%d-%02d-%02d' % (year, month, day)
        return text

    def normalize_num(self, text):
        coeff = 1.0
        if '亿' in text:
            coeff *= 100000000
        if '万' in text:
            coeff *= 10000
        if '千' in text or '仟' in text:
            coeff *= 1000
        if '百' in text or '佰' in text:
            coeff *= 100
        if '%' in text:
            coeff *= 0.01
        try:
            number = float(TextUtils.extract_number(text))
            number_text = '%.4f' % (number * coeff)
            if number_text.endswith('.0'):
                return number_text[:-2]
            elif number_text.endswith('.00'):
                return number_text[:-3]
            elif number_text.endswith('.000'):
                return number_text[:-4]
            elif number_text.endswith('.0000'):
                return number_text[:-5]
            else:
                if '.' in number_text:
                    idx = len(number_text)
                    while idx > 1 and number_text[idx-1] == '0':
                        idx -= 1
                    number_text = number_text[:idx]
                return number_text
        except:
            return text


    def normalize(self):
        if self.finishDate is not None:
            self.finishDate = self.normalize_finish_date(self.finishDate)
        if self.shareNum is not None:
            self.shareNum = self.normalize_num(self.shareNum)
        if self.shareNumAfterChg is not None:
            self.shareNumAfterChg = self.normalize_num(self.shareNumAfterChg)
        if self.sharePcntAfterChg is not None:
            self.sharePcntAfterChg = self.normalize_num(self.sharePcntAfterChg)

    def to_result(self):
        self.normalize()
        return "%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
        # return "%s(full)\t%s(short)\t%s(date)\t%s(price)\t%s(num)\t%s(numAfter)\t%s(pcntAfter)" % (
            self.shareholderFullName if self.shareholderFullName is not None else '',
            self.shareholderShortName if self.shareholderShortName is not None else '',
            self.finishDate if self.finishDate is not None else '',
            self.sharePrice if self.sharePrice is not None else '',
            self.shareNum if self.shareNum is not None else '',
            self.shareNumAfterChg if self.shareNumAfterChg is not None else '',
            self.sharePcntAfterChg if self.sharePcntAfterChg is not None else '')


class ZengJianChiExtractor(object):

    def __init__(self, config_file_path, ner_model_dir_path, ner_blacklist_file_path):
        self.html_parser = HTMLParser.HTMLParser()
        self.config = None
        self.ner_tagger = NERTagger.NERTagger(ner_model_dir_path, ner_blacklist_file_path)
        self.com_abbr_dict = {}
        self.com_full_dict = {}
        self.com_abbr_ner_dict = {}

        with codecs.open(config_file_path, encoding='utf-8', mode='r') as fp:
            self.config = json.loads(fp.read())
        self.table_dict_field_pattern_dict = {}
        for table_dict_field in self.config['table_dict']['fields']:
            field_name = table_dict_field['fieldName']
            if field_name is None:
                continue
            convert_method = table_dict_field['convertMethod']
            if convert_method is None:
                continue
            pattern = table_dict_field['pattern']
            if pattern is None:
                continue
            col_skip_pattern = None
            if 'colSkipPattern' in table_dict_field:
                col_skip_pattern = table_dict_field['colSkipPattern']
            row_skip_pattern = None
            if 'rowSkipPattern' in table_dict_field:
                row_skip_pattern = table_dict_field['rowSkipPattern']
            self.table_dict_field_pattern_dict[field_name] = \
                TableDictFieldPattern(field_name=field_name, convert_method=convert_method,
                                      pattern=pattern, col_skip_pattern=col_skip_pattern,
                                      row_skip_pattern=row_skip_pattern)


    def extract_from_table_dict(self, table_dict):
        rs = []
        if table_dict is None or len(table_dict) <= 0:
            return rs
        row_length = len(table_dict)
        field_col_dict = {}
        skip_row_set = set()
        # 1. 假定第一行是表头部分则尝试进行规则匹配这一列是哪个类型的字段
        # 必须满足 is_match_pattern is True and is_match_col_skip_pattern is False
        head_row = table_dict[0]
        col_length = len(head_row)
        for i in range(col_length):
            text = head_row[i]
            for (field_name, table_dict_field_pattern) in self.table_dict_field_pattern_dict.items():
                if table_dict_field_pattern.is_match_pattern(text) and \
                        not table_dict_field_pattern.is_match_col_skip_pattern(text):
                    if field_name not in field_col_dict:
                        field_col_dict[field_name] = i
                    # 逐行扫描这个字段的取值，如果满足 row_skip_pattern 则丢弃整行 row
                    for j in range(1, row_length):
                        try:
                            text = table_dict[j][i]
                            if table_dict_field_pattern.is_match_row_skip_pattern(text):
                                skip_row_set.add(j)
                        except KeyError:
                            pass
        if len(field_col_dict) <= 0:
            return rs
        # 2. 遍历每个有效行，获取 record
        for row_index in range(1, row_length):
            if row_index in skip_row_set:
                continue
            record = ZengJianChiRecord(None, None, None, None, None, None, None)
            for (field_name, col_index) in field_col_dict.items():
                try:
                    text = table_dict[row_index][col_index]
                    if field_name == 'shareholderFullName':
                        record.shareholderFullName = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    elif field_name == 'finishDate':
                        record.finishDate = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    elif field_name == 'sharePrice':
                        record.sharePrice = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    elif field_name == 'shareNum':
                        record.shareNum = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    elif field_name == 'shareNumAfterChg':
                        record.shareNumAfterChg = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    elif field_name == 'sharePcntAfterChg':
                        record.sharePcntAfterChg = self.table_dict_field_pattern_dict.get(field_name).convert(text)
                    else:
                        pass
                except KeyError:
                    pass
            rs.append(record)
        return rs


    def extract_from_paragraphs(self, paragraphs):
        self.clearComAbbrDict()
        change_records = []
        change_after_records = []
        record_list = []
        for para in paragraphs:
            change_records_para, change_after_records_para = self.extract_from_paragraph(para)
            change_records += change_records_para
            change_after_records += change_after_records_para
        self.mergeRecord(change_records, change_after_records)
        for record in change_records:
            record_list.append(record)
        return record_list


    def extract_company_name(self, paragraph):
        # print(paragraph)
        targets = re.finditer(r"<org>(?P<com>.{1,28}?)</org>[(（].{0,5}?简称:?[\"“](?P<com_abbr>.{2,6}?)[\"”][)）]", paragraph)
        size_before = len(self.com_abbr_ner_dict)
        for target in targets:
            # print("===> ", target.group())
            com_abbr = target.group("com_abbr")
            com_name = target.group("com")
            if com_abbr != None and com_name != None:
                self.com_abbr_dict[com_abbr] = com_name
                self.com_full_dict[com_name] = com_abbr
                self.com_abbr_ner_dict[com_abbr] = "Ni"
        return len(self.com_abbr_ner_dict) - size_before

    def extract_from_paragraph(self, paragraph):
        tag_res = self.ner_tagger.ner(paragraph, self.com_abbr_ner_dict)
        tagged_str = tag_res.get_tagged_str()
        #抽取公司简称
        new_size = self.extract_company_name(tagged_str)
        if new_size > 0:
            tag_res = self.ner_tagger.ner(paragraph, self.com_abbr_ner_dict)
            tagged_str = tag_res.get_tagged_str()

        change_records = self.extract_change(tagged_str)
        change_after_records = self.extract_change_after(tagged_str)
        return change_records,change_after_records

    def mergeRecord(self, changeRecords, changeAfterRecords):
        if len(changeRecords) == 0 or len(changeAfterRecords) == 0:
            return
        last_record = None
        for record in changeRecords:
            if last_record != None and record.shareholderFullName != last_record.shareholderFullName:
                self.mergeChangeAfterInfo(last_record,changeAfterRecords)
            last_record = record
        self.mergeChangeAfterInfo(last_record,changeAfterRecords)

    def mergeChangeAfterInfo(self, changeRecord, changeAfterRecords):
        for record in changeAfterRecords:
            if record.shareholderFullName == changeRecord.shareholderFullName:
                changeRecord.shareNumAfterChg = record.shareNumAfterChg
                changeRecord.sharePcntAfterChg = record.sharePcntAfterChg

    def extract_change(self, paragraph):
        records = []
        targets = re.finditer(r"(出售|减持|增持|买入)了?[^，。,:;!?？]*?(股票|股份).{0,30}?<num>(?P<share_num>.{1,20}?)</num>股", paragraph)
        for target in targets:
            share_num = target.group("share_num")
            start_pos = target.start()
            end_pos = target.end()
            #查找公司
            pat_com = re.compile(r"<org>(.*?)</org>")
            m_com = pat_com.findall(paragraph,0,end_pos)
            shareholder = ""
            if m_com != None and len(m_com) > 0:
                shareholder = m_com[-1]
            else :
                pat_person = re.compile(r"<person>(.*?)</person>")
                m_person = pat_person.findall(paragraph,0,end_pos)
                if m_person != None and len(m_person) > 0 :
                    shareholder = m_person[-1]
            #查找日期
            pat_date = re.compile(r"<date>(.*?)</date>")
            m_date = pat_date.findall(paragraph,0,end_pos)
            change_date = ""
            if m_date != None and len(m_date)>0:
                change_date = m_date[-1]
            #查找变动价格
            pat_price = re.compile(r"(均价|平均(增持|减持|成交)?(价格|股价))(:|：)?<num>(?P<share_price>.*?)</num>")
            m_price = pat_price.search(paragraph,start_pos)
            share_price = ""
            if m_price != None:
                share_price = m_price.group("share_price")
            if shareholder == None or len(shareholder) == 0:
                continue
            full_name,short_name = self.getShareholder(shareholder)
            records.append(ZengJianChiRecord(full_name, short_name, change_date, share_price, share_num,"", ""))
        return records


    def extract_change_after(self, paragraph):
        records = []
        targets = re.finditer(r"(增持后|减持后|变动后).{0,30}?持有.{0,30}?<num>(?P<share_num_after>.*?)</num>(股|万股|百万股|亿股)", paragraph)
        for target in targets:
            share_num_after = target.group("share_num_after")
            start_pos = target.start()
            end_pos = target.end()
            #查找公司
            pat_com = re.compile(r"<org>(.*?)</org>")
            m_com = pat_com.findall(paragraph,0,end_pos)
            shareholder = ""
            if m_com != None and len(m_com) > 0:
                shareholder = m_com[-1]
            else :
                pat_person = re.compile(r"<person>(.*?)</person>")
                m_person = pat_person.findall(paragraph,0,end_pos)
                if m_person != None and len(m_person) > 0:
                    shareholder = m_person[-1]
            #查找变动后持股比例
            pat_percent_after = re.compile(r"<percent>(?P<share_percent>.*?)</percent>")
            m_percent_after = pat_percent_after.search(paragraph,start_pos)
            share_percent_after = ""
            if m_percent_after != None:
                share_percent_after = m_percent_after.group("share_percent")
            if shareholder == None or len(shareholder) == 0:
                continue
            full_name,short_name = self.getShareholder(shareholder)
            records.append(ZengJianChiRecord(full_name,short_name, "", "", "", share_num_after, share_percent_after))
        return records

    def clearComAbbrDict(self):
        self.com_abbr_dict = {}
        self.com_full_dict = {}
        self.com_abbr_ner_dict = {}

    def getShareholder(self, shareholder):
        #归一化公司全称简称
        if shareholder in self.com_full_dict:
            return shareholder, self.com_full_dict.get(shareholder, "")
        if shareholder in self.com_abbr_dict:
            return self.com_abbr_dict.get(shareholder, ""),shareholder
        #股东为自然人时不需要简称
        return shareholder, ""

    def extract(self, html_file_path):
        # 1. 解析 Table Dict
        rs = []
        paragraphs = self.html_parser.parse_content(html_file_path)
        rs_paragraphs = self.extract_from_paragraphs(paragraphs)
        for table_dict in self.html_parser.parse_table(html_file_path):
            rs_table = self.extract_from_table_dict(table_dict)
            if len(rs_table) > 0:
                if len(rs) > 0:
                    self.mergeRecord(rs, rs_table)
                    break
                else:
                    rs.extend(rs_table)
        # 2. 如果没有 Table Dict 则解析文本部分
        if len(rs) <= 0:
            return rs_paragraphs
        else:
            for record in rs:
                full_company_name, abbr_company_name = self.getShareholder(record.shareholderFullName)
                if full_company_name is not None and len(full_company_name) > 0 \
                        and abbr_company_name is not None and len(abbr_company_name) > 0:
                    record.shareholderFullName = full_company_name
                    record.shareholderShortName = abbr_company_name
                else:
                    record.shareholderShortName = record.shareholderFullName
        return rs


class TableDictFieldPattern(object):
    def __init__(self, field_name, convert_method, pattern, col_skip_pattern, row_skip_pattern):
        self.field_name = field_name
        self.convert_method = convert_method
        self.pattern = None
        if pattern is not None and len(pattern) > 0:
            self.pattern = re.compile(pattern)
        self.col_skip_pattern = None
        if col_skip_pattern is not None and len(col_skip_pattern) > 0:
            self.col_skip_pattern = re.compile(col_skip_pattern)
        self.row_skip_pattern = None
        if row_skip_pattern is not None and len(row_skip_pattern) > 0:
            self.row_skip_pattern = re.compile(row_skip_pattern)

    def is_match_pattern(self, text):
        if self.pattern is None:
            return False
        match = self.pattern.search(text)
        return True if match else False

    def is_match_col_skip_pattern(self, text):
        if self.col_skip_pattern is None:
            return False
        match = self.col_skip_pattern.search(text)
        return True if match else False

    def is_match_row_skip_pattern(self, text):
        if self.row_skip_pattern is None:
            return False
        match = self.row_skip_pattern.search(text)
        return True if match else False

    def get_field_name(self):
        return self.field_name

    def convert(self, text):
        if self.convert_method is None:
            return self.default_convert(text)
        elif self.convert_method == 'getStringFromText':
            return self.getStringFromText(text)
        elif self.convert_method == 'getDateFromText':
            return self.getDateFromText(text)
        elif self.convert_method == 'getLongFromText':
            return self.getLongFromText(text)
        elif self.convert_method == 'getDecimalFromText':
            return self.getDecimalFromText(text)
        elif self.convert_method == 'getDecimalRangeFromTableText':
            return self.getDecimalRangeFromTableText(text)
        else:
            return self.default_convert(text)

    @staticmethod
    def default_convert(text):
        return text

    @staticmethod
    def getStringFromText(text):
        return text

    @staticmethod
    def getDateFromText(text):
        strList = text.split("至")
        if len(strList) < 2 and ("月" in text or "年" in text or "/" in text or "." in text):
            strList = re.split("-|—|~", text)
        return strList[-1]

    @staticmethod
    def getLongFromText(text):
        return TextUtils.remove_comma_in_number(text)

    @staticmethod
    def getDecimalFromText(text):
        return text

    @staticmethod
    def getDecimalRangeFromTableText(text):
        return text


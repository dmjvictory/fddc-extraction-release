#!/bin/python
# -*- coding: utf-8 -*-

import os
import re
from pyltp import NamedEntityRecognizer,Segmentor,Postagger,SentenceSplitter


class NERTaggedText(object):

    def __init__(self, text, tagged_seg_list):
        self.text = text
        self.tagged_seg_list = tagged_seg_list
        self.valid_tag_set = set(['Nh', 'Ni', 'nt', 'v', 'm', 'q'])
        self.tag_entity_dict = {'Nh':'person','Ni':'org','nt':'date','m':'num','mp':'percent'}

    def get_tagged_seg_list(self):
        return self.tagged_seg_list

    def get_filtered_tagged_seg_list(self):
        rs_list = []
        for tagged_seg in self.tagged_seg_list:
            if tagged_seg[1] in self.valid_tag_set:
                rs_list.append(tagged_seg)
        return rs_list

    def get_tagged_str(self):
        tagged_str = ""
        for word,tag in self.tagged_seg_list:
            if tag in self.tag_entity_dict:
                tagged_str += "<%s>%s</%s>"%(self.tag_entity_dict[tag],word,self.tag_entity_dict[tag])
            else:
                tagged_str += word
        return tagged_str

class NERTagger(object):

    def __init__(self, model_dir_path, com_blacklist):
        # 初始化相关模型文件路径
        self.model_dir_path = model_dir_path
        self.cws_model_path = os.path.join(self.model_dir_path, 'cws.model')  # 分词模型路径，模型名称为`cws.model`
        self.pos_model_path = os.path.join(self.model_dir_path, 'pos.model')  # 词性标注模型路径，模型名称为`pos.model`
        self.ner_model_path = os.path.join(self.model_dir_path, 'ner.model')  # 命名实体识别模型路径，模型名称为`pos.model`

        # 初始化分词模型
        self.segmentor = Segmentor()
        self.segmentor.load(self.cws_model_path)

        # 初始化词性标注模型
        self.postagger = Postagger()
        self.postagger.load(self.pos_model_path)

        # 初始化NER模型
        self.recognizer = NamedEntityRecognizer()
        self.recognizer.load(self.ner_model_path)

        # 初始化公司名黑名单
        self.com_blacklist = set()
        with open(com_blacklist) as f_com_blacklist:
            for line in f_com_blacklist:
                if len(line.strip()) > 0:
                    self.com_blacklist.add(line.strip())


    def ner(self, text, entity_dict):
        words = self.segmentor.segment(text)  # 分词
        post_tags = self.postagger.postag(words)
        ner_tags = self.recognizer.recognize(words, post_tags)  # 命名实体识别
#        print('\t'.join(words))
#        print('\t'.join(post_tags))
#        print('\t'.join(ner_tags))
#        print('-' * 80)
        entity_list = []
        entity = ""
        for word, post_tag, ner_tag in zip(words, post_tags, ner_tags):
            tag = ner_tag[0]
            entity_type = ner_tag[2:]
            if tag == 'S' :
                entity_list.append((word, entity_type))
            elif tag in 'BIE':
                entity += word
                if tag == 'E':
                    #判断公司名黑名单
                    if entity in self.com_blacklist:
                        entity_list.append((entity, "n"))
                    else:
                        entity_list.append((entity, entity_type))
                    entity = ""
            elif tag == 'O':
                if post_tag == 'nt':
                    entity += word
                else:
                    if entity != "":
                        entity_list.append((entity, 'nt'))
                        entity = ""
                    # 排除错误数字识别，例如“大宗”
                    if post_tag == 'm' and not re.match("[0-9]+.*",word):
                        post_tag = 'n'
                    # 识别数字中的百分数
                    if post_tag == 'm' and re.match("[0-9.]+%",word):
                        post_tag = 'mp'
                    entity_list.append((word, post_tag))
        entity_list = self.ner_tag_by_dict(entity_dict, entity_list)
        return NERTaggedText(text, entity_list)

    def ner_tag_by_dict(self, entity_dict, entity_list):
#        for item in entity_dict.items():
#            print("\t".join(item))
        i = 0
        while i < len(entity_list) - 1:
            has_entity = False
            for entity_len in range(4,1,-1):
                segment = "".join([ x[0] for x in entity_list[i:i+entity_len]])
                # segment_uni = segment.decode('utf-8')
                segment_uni = segment
                if segment_uni in entity_dict:
                    has_entity = True
                    entity_list[i] = (segment,entity_dict[segment_uni])
                    del entity_list[i+1:i+entity_len]
                    i = i + entity_len
                    break
            if not has_entity:
                i += 1
        return entity_list


    def __del__(self):
        self.segmentor.release()
        self.postagger.release()
        self.recognizer.release()


if __name__ == "__main__":
    text = "2018年4月25日，公司收到证券公司的通知：证券公司已于2018年4 月25日处置了钟波先生质押标的证券，违约处置数量为90.3万股，成交金额779.4482万元，平均成交价8.632元/股。本次减持前，钟波先生持有公司股份1000万股，占公司总股本的2.77%。本次减持后，钟波先生持有公司股份909.7万股，占公司总股本的2.52%。"
    # text = "2018年4月24日、4月25日，公司实际控制人之一黄盛秋先生因股票质押违约，被证券公司强行平仓247.65万股。2018年4月25日，公司实际控制人之一钟波先生因股票质押违约，被证券公司强行平仓90.3万股。上述二人合计被强行平仓337.95万股，占公司总股本的0.94%，根据相关规定，公司实际控制人以集中竞价方式减持公司股份在任意连续九十个自然日内，减持股份的总数不得超过公司股份总数的百分之一即361.43万股。"
    # text = '中华人民共和国中央人民政府于1949年10月1日在伟大首都北京成立了'
    ner_tagger = NERTagger("model/ltp_data_v3.4.0","config/ner_com_blacklist.txt")

    res = ner_tagger.ner(text,{"标的证券":"Ni"})
    for ent in res.get_tagged_seg_list():
        print('\t'.join(ent))
    print(res.get_tagged_str())

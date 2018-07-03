# FDDC2018金融算法挑战赛02－A股上市公司公告信息抽取

## 基本信息

* config： 目录包含一些配置文件
* docparser： 实现对文档的解析，主要是对HTML文件的解析，解析HTML中的文本段落和表格信息
* extract: 实现信息抽取器，主要基于docparser解析后的结果进行信息抽取，这里主要实现了增减持项目的抽取器
* ner: 封装实现 NER打标签的工具
* utils: 实现一些功能性组件
* app.py: 主函数，实现对某篇HTML文件或某个目录下HTML文件的信息抽取
* requirements.txt： pip 的相关依赖列表


## 运行方法

运行python环境为： python3.6
NER部分采用 [pyltp](http://pyltp.readthedocs.io/zh_CN/develop/api.html) 需要下载相关模型文件并在app.py中配置相关模型目录路径 ner_model_dir_path


```bash
# 安装相关依赖
pip install -r requirements.txt

# 运行增减持抽取
python app.py > result.txt

```
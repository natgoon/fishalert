
class Config(object):


    listenPort = 5000
    listenHost = '0.0.0.0'

    #连接mysql
    mysql_host = '192.168.4.103'
    mysql_port = 21410
    mysql_user = 'bptest'
    mysql_password = 'bptest'
    mysql_database = 'fishalert'

    #连接mongodb
    mongo_host = '192.168.0.102'
    mongo_port = 27017


    #默认告警模板与媒介
    sendway = 'wechat'
    sentto = 'nat.zhu'
    template = '告警主题: {{alertname}}\n告警值: {{value}}\n告警类型: {{alertType}}\n告警时间: {{alertAt}}\n告警来源: {{alertSource}}'
    prometheus_template = '告警主题: {{alertname}}\n告警值: {{value}}\n告警类型: {{alertType}}\n告警时间: {{alertAt}}\n告警来源: {{alertSource}}'
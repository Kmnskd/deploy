#!/usr/bin/env python3

from settings import SERVICE_INFO
from settings import NACOS_NAMESPACE
from settings import TAG_NAME
from settings import HARBOR_IP
from settings import ACK

import subprocess
import os
import sys
import requests
import urllib3
urllib3.disable_warnings()


class BaselineError(Exception):
    pass


class AutomationDeploy(object):
    """ 自动化部署脚本 """

    def __init__(self):
        self.service_info = SERVICE_INFO
        self.tag_name = TAG_NAME
        self.nacos_namespace = NACOS_NAMESPACE
        self.current_env = None
        self.harbor_ip = HARBOR_IP
        self.ack = ACK

    def modify_dockerfile(self, jar_name, namespace):
        """ 根据部署环境修改dockerfile的参数 """
        service_name = jar_name.split("-1.0.0.jar")[0]
        port = self.service_info.get(service_name).get("service_port")
        status, output = self.run_cmd(
            "sed -i 's/service_port/%s/g' deploy/Dockerfile && "
            "sed -i 's/baseline.jar/%s/g' deploy/Dockerfile && "
            "sed -i 's/current-env/%s/g' deploy/Dockerfile && "
            "sed -i 's/nacos-namespace/%s/g' deploy/Dockerfile" %
            (port, jar_name, self.current_env, namespace))
        if status:
            raise BaselineError(output)
        return port

    def copy_jar(self):
        devp_file = os.listdir()
        for i in devp_file:
            if "devp" in i:
                cmd = 'cp %s/target/*.jar deploy' % i
                self.run_cmd(cmd)

        module_file = os.listdir("baseline-modules")
        for i in module_file:
            if "baseline" in i:
                cmd = 'cp baseline-modules/%s/target/*.jar deploy' % i
                self.run_cmd(cmd)

    def login_harbor(self):
        self.run_cmd(
            "docker login -u admin -p Harbor12345 http://%s" % self.harbor_ip)

    def build_image(self, service_name, tag):
        """ 制作镜像及推送镜像 """
        namespace = self.nacos_namespace.get(self.current_env)
        for name in service_name:
            print("**********START BUILD SERVICE************")
            name = name.split("/")[-1]
            print("start build %s image, and push to harbor." % name)
            port = self.modify_dockerfile(name, namespace)
            self.get_cmd(name, tag)
            print("%s build and push image successful." % name)
            # 把dockerfile还原，下一次sed直接替换80端口
            self.run_cmd(
                "sed -i 's/%s/service_port/g' deploy/Dockerfile && "
                "sed -i 's/%s/baseline.jar/g' deploy/Dockerfile && "
                "sed -i 's/%s/current-env/g' deploy/Dockerfile && "
                "sed -i 's/%s/nacos-namespace/g' deploy/Dockerfile" %
                (port, name, self.current_env, namespace))

            print("**********END BUILD SERVICE************\n")

    def delete_images(self):
        delete_image = "docker rmi -f $(docker images | grep baseline | awk '{print $3}')"
        self.run_cmd(delete_image)

    def deploy_image(self, tag):
        self.update_kube_config("start")
        temp = tag
        # 由于生产环境可能出现同一个tag打多次的情况，拉取镜像如果tag相同默认不更新，所以生产环境需要以哈希值拉镜像，不能以tag为准
        for name in self.service_info:
            yaml_name = name + ".yaml"
            node_port = self.service_info.get(name).get(
                "node_port").get(self.current_env)
            if self.current_env == "prd":
                current_tag = temp
                image_sha256 = self.get_images_sha256(current_tag, name)
                tag = "@" + image_sha256
            else:
                tag = ":" + temp
            self.create_k8s_yaml(tag, name, node_port, yaml_name)
        self.update_kube_config("finish")

    def update_kube_config(self, condition):
        if not self.ack_bool:
            return
        cmd = ""
        if condition == "start":
            if self.current_env == "prd":
                cmd = "mv ~/.kube/config_106 ~/.kube/config"
            else:
                cmd = "mv ~/.kube/config_167 ~/.kube/config"
        elif condition == "finish":
            if self.current_env == "prd":
                cmd = "mv ~/.kube/config ~/.kube/config_106"
            else:
                cmd = "mv ~/.kube/config ~/.kube/config_167"

        self.run_cmd(cmd)

    def create_k8s_yaml(self, tag, name, node_port, yaml_name):
        print(
            "START DEPLOY %s SERVICE to k8s %s ENV" %
            (name, self.current_env))
        update_yaml = "sed -i -e 's/tag-name/%s/g' -e 's/\\<current-env\\>/%s/g' -e 's/node-port/%s/g' -e 's/\\<replicas-num\\>/%s/g' deploy/%s" \
                      % (tag, self.current_env, node_port, 1, yaml_name)
        self.run_cmd(update_yaml)
        cmd = "kubectl apply -f deploy/%s" % yaml_name
        # cmd = "cat deploy/%s" % yaml_name
        self.run_cmd(cmd)

        # 还原默认yaml
        reduction_yaml = "sed -i -e 's/%s/tag-name/g' -e 's/\\<%s\\>/current-env/g' -e 's/%s/node-port/g' -e 's/\\<%s\\>/replicas-num/g' deploy/%s" \
                         % (tag, self.current_env, node_port, 1, yaml_name)
        self.run_cmd(reduction_yaml)
        print(
            "END DEPLOY %s SERVICE to k8s %s ENV\n" %
            (name, self.current_env))

    def get_name(self):
        """ 获取要部署的jar包 """
        try:
            status, service_name = self.run_cmd(
                "ls deploy/*.jar |grep -v 'api.jar'|grep -v 'common'|grep -v 'demo'")
            if status:
                raise BaselineError("get service name error: %s.")
            return service_name.split()
        except Exception as e:
            raise BaselineError(e)

    def get_env(self, tag):
        '''
        :param tag: 例如tag号为4.0.3.2.202110131122, 4.0.3为当前版本号，2为分支代号，202110131122为时间戳
            部署环境对应tag
            {"4.0.3": "prd", "4.0.3.1.202110131122": "test", "4.0.3.2.202110131122": "dev"}
        :return: tag
        '''
        tag_list = tag.split(".")
        if len(tag_list) == 3:
            self.current_env = "prd"
            # 生产不配置运营平台的域名解析
            self.run_cmd("sed -i '/47.93.125.250/,/zj.haier.net/d' deploy/devp-client-integration.yaml")
            return
        tag_num = tag_list[-2]
        self.current_env = self.tag_name.get(tag_num, "")
        self.ack_judge(self.current_env)
        if not self.current_env:
            print("tag name is error.tag: %s" % tag)
            raise BaselineError("tag name is error.")

    def get_cmd(self, service_name, tag):
        """ 制作镜像及推送镜像"""
        service_name = service_name.split("-")
        service = "-".join(service_name[:-1])
        build_cmd = "docker build -f deploy/Dockerfile -t %s:%s deploy" % (
            service, tag)
        tag_cmd = "docker tag %s:%s %s/baseline-%s/%s:%s" % (
            service, tag, self.harbor_ip, self.current_env, service, tag)
        push_cmd = "docker push %s/baseline-%s/%s:%s" % (
            self.harbor_ip, self.current_env, service, tag)
        cmd_list = [build_cmd, tag_cmd, push_cmd]
        for cmd in cmd_list:
            self.run_cmd(cmd)

    @staticmethod
    def run_cmd(cmd):
        """ 执行sh命令 """
        ret = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, encoding="utf-8")
        status = ret.returncode
        if status == 0:
            print("run cmd: %s. success status: %s " % (cmd, status))
            return status, ret.stdout
        else:
            print(
                "run cmd: %s, status: %s, error: %s " %
                (cmd, status, ret.stderr))
            if "cp" not in cmd:
                sys.exit(1)

    def get_images_sha256(self, current_tag, service_name):
        """ 获取image的哈希值 """
        headers = {"Content-Type": "application/json"}
        get_url = "http://%s/api/v2.0/projects/baseline-prd/repositories/%s/artifacts" \
                  "?with_tag=true&with_scan_overview=true&with_label=true&page_size=1" % (self.harbor_ip, service_name)
        res = requests.get(headers=headers, url=get_url, verify=False)
        data = res.json()
        for i in data:
            tag_name = i.get("tags")[0].get("name")
            if tag_name == current_tag:
                return i.get("digest")

    def backup_mysql(self, tag):
        if self.current_env == "prd":
            cmd = "ssh jenkins@10.163.205.239 /bin/bash /data/zone_mysql/backup.sh %s" % tag
            self.run_cmd(cmd)

    def ack_judge(self, num_label):
        if num_label in self.ack:
            self.ack_bool = True
            # 由于feature空间kusphere和ack都存在，所以需要特殊处理，nacos的空间id是相同的
            if self.current_env == "ack_feature":
                self.current_env = "feature"

    def auto_build(self, tag):
        # copy jar包
        self.copy_jar()
        # 获取当前所有需要制作镜像的服务
        service_name = self.get_name()
        # 根据tag识别当前分支并部署到不同部署环境
        self.get_env(tag)
        # 登录harbor
        self.login_harbor()
        # 制作镜像
        # self.build_image(service_name, tag)
        # 部署镜像
        self.deploy_image(tag)
        # 生产数据库备份
        # self.backup_mysql(tag)
        # 删除镜像
        # self.delete_images()


if __name__ == '__main__':
    auto = AutomationDeploy()
    tag = sys.argv[1]
    auto.auto_build(tag)
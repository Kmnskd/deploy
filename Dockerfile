FROM apache/skywalking-java-agent:8.8.0-java8

MAINTAINER likunkun@haier.com
ENV LANG C.UTF-8
ENV TIME_ZONE Asia/Shanghai
ENV SERVICE_PACKAGE_NAME baseline.jar
ENV CODE_PATH /usr/local/bin/baseline
ENV NACOS_SERVER baseline-nacos.zone-current-env
ENV NACOS_NAMESPACE nacos-namespace
ENV ACTIVE current-env
ENV PORT service_port

ADD $SERVICE_PACKAGE_NAME $CODE_PATH/$SERVICE_PACKAGE_NAME

EXPOSE $PORT

RUN ln -snf /usr/share/zoneinfo/$TIME_ZONE /etc/localtime && echo $TIME_ZONE > /etc/timezone

ENTRYPOINT java -jar $CODE_PATH/$SERVICE_PACKAGE_NAME --spring.profiles.active=$ACTIVE --spring.cloud.nacos.config.server-addr=$NACOS_SERVER --spring.cloud.nacos.config.namespace=$NACOS_NAMESPACE

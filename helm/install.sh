#!/bin/bash

namespace=$1

sed -i 's/zone-eureka/${namespace}/g' *.yaml
sed -i 's/zone-eureka/${namespace}/g' rocketmq/*.yaml

kubectl create namespace ${namespace}
kubectl apply -f mockserver.yaml
kubectl apply -f mysql.yaml
kubectl apply -f nacos.yaml
kubectl apply -f redis.yaml

kubectl apply -f rokcetmq/rocketmq_v1alpha1_broker_crd.yaml
kubectl apply -f rokcetmq/rocketmq_v1alpha1_nameservice_crd.yaml
kubectl apply -f rokcetmq/rocketmq_v1alpha1_consoles_crd.yaml
kubectl apply -f rokcetmq/rocketmq_v1alpha1_topictransfer_crd.yaml
kubectl apply -f rokcetmq/service_account.yaml
kubectl apply -f rokcetmq/role.yaml
kubectl apply -f rokcetmq/role_binding.yaml
kubectl apply -f rokcetmq/operator.yaml
kubectl apply -f rokcetmq/rocketmq_v1alpha1_rocketmq_cluster.yaml
kubectl apply -f rokcetmq/rocketmq.yaml

sed -i 's/${namespace}/zone-eureka/g' *.yaml
sed -i 's/${namespace}/zone-eureka/g' rocketmq/*.yaml
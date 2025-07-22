package com.example.prometheusrocketmqadapter.service;

import com.example.prometheusrocketmqadapter.dto.MetricMessage;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.rocketmq.client.consumer.DefaultMQPushConsumer;
import org.apache.rocketmq.client.consumer.listener.ConsumeConcurrentlyStatus;
import org.apache.rocketmq.client.consumer.listener.MessageListenerConcurrently;
import org.apache.rocketmq.client.exception.MQClientException;
import org.apache.rocketmq.common.message.MessageExt;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import javax.annotation.PreDestroy;
import java.io.IOException;
import java.util.List;

@Service
public class RocketMQConsumerService {

    @Value("${rocketmq.name-server}")
    private String nameServer;

    @Value("${rocketmq.consumer.group}")
    private String consumerGroup;

    @Value("${rocketmq.consumer.topic}")
    private String topic;

    private DefaultMQPushConsumer consumer;

    private final PrometheusService prometheusService;
    private final ObjectMapper objectMapper;

    public RocketMQConsumerService(PrometheusService prometheusService, ObjectMapper objectMapper) {
        this.prometheusService = prometheusService;
        this.objectMapper = objectMapper;
    }

    @PostConstruct
    public void start() throws MQClientException {
        consumer = new DefaultMQPushConsumer(consumerGroup);
        consumer.setNamesrvAddr(nameServer);
        consumer.subscribe(topic, "*");
        consumer.registerMessageListener((MessageListenerConcurrently) (msgs, context) -> {
            for (MessageExt msg : msgs) {
                try {
                    MetricMessage message = objectMapper.readValue(msg.getBody(), MetricMessage.class);
                    prometheusService.createOrUpdateGauge(message.getMetricName(), message.getMetricValue(), message.getLabels());
                } catch (IOException e) {
                    // Handle JSON parsing error
                    e.printStackTrace();
                }
            }
            return ConsumeConcurrentlyStatus.CONSUME_SUCCESS;
        });
        consumer.start();
        System.out.println("RocketMQ consumer started.");
    }

    @PreDestroy
    public void shutdown() {
        if (consumer != null) {
            consumer.shutdown();
            System.out.println("RocketMQ consumer shutdown.");
        }
    }
}

package com.example.prometheusrocketmqadapter.service;

import io.prometheus.client.CollectorRegistry;
import io.prometheus.client.Gauge;
import org.springframework.stereotype.Service;

import java.util.Map;

@Service
public class PrometheusService {

    private final CollectorRegistry collectorRegistry;

    public PrometheusService(CollectorRegistry collectorRegistry) {
        this.collectorRegistry = collectorRegistry;
    }

    public void createOrUpdateGauge(String metricName, double value, Map<String, String> labels) {
        Gauge gauge = Gauge.build()
                .name(metricName)
                .help("Gauge for " + metricName)
                .labelNames(labels.keySet().toArray(new String[0]))
                .register(collectorRegistry);

        gauge.labels(labels.values().toArray(new String[0])).set(value);
    }
}

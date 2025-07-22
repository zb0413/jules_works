package com.example.prometheusrocketmqadapter.service;

import com.example.prometheusrocketmqadapter.prometheus.Remote;
import com.example.prometheusrocketmqadapter.prometheus.Types;
import io.prometheus.client.Collector;
import io.prometheus.client.CollectorRegistry;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.xerial.snappy.Snappy;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Enumeration;

@Service
public class PrometheusRemoteWriteService {

    @Value("${prometheus.remote-write.url}")
    private String remoteWriteUrl;

    private final CollectorRegistry collectorRegistry;

    public PrometheusRemoteWriteService(CollectorRegistry collectorRegistry) {
        this.collectorRegistry = collectorRegistry;
    }

    @Scheduled(fixedRate = 15000) // Push metrics every 15 seconds
    public void pushMetrics() {
        try {
            Remote.WriteRequest.Builder writeRequestBuilder = Remote.WriteRequest.newBuilder();
            Enumeration<Collector.MetricFamilySamples> mfs = collectorRegistry.metricFamilySamples();
            while (mfs.hasMoreElements()) {
                Collector.MetricFamilySamples metricFamilySamples = mfs.nextElement();
                for (Collector.MetricFamilySamples.Sample sample : metricFamilySamples.samples) {
                    Types.TimeSeries.Builder timeSeriesBuilder = Types.TimeSeries.newBuilder();
                    timeSeriesBuilder.addLabels(
                            Types.Label.newBuilder().setName("__name__").setValue(sample.name).build());
                    for (int i = 0; i < sample.labelNames.size(); i++) {
                        timeSeriesBuilder.addLabels(
                                Types.Label.newBuilder().setName(sample.labelNames.get(i)).setValue(sample.labelValues.get(i)).build());
                    }
                    timeSeriesBuilder.addSamples(
                            Types.Sample.newBuilder().setValue(sample.value).setTimestamp(System.currentTimeMillis()).build());
                    writeRequestBuilder.addTimeseries(timeSeriesBuilder.build());
                }
            }

            byte[] compressed = Snappy.compress(writeRequestBuilder.build().toByteArray());

            URL url = new URL(remoteWriteUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/x-protobuf");
            conn.setRequestProperty("Content-Encoding", "snappy");
            conn.setRequestProperty("X-Prometheus-Remote-Write-Version", "0.1.0");

            conn.getOutputStream().write(compressed);
            conn.getOutputStream().close();

            int responseCode = conn.getResponseCode();
            if (responseCode != HttpURLConnection.HTTP_NO_CONTENT) {
                // Handle non-successful response
                System.err.println("Failed to write metrics to Prometheus, response code: " + responseCode);
            }

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}

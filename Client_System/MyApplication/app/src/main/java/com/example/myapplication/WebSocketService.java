package com.example.myapplication;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import org.json.JSONException;
import org.json.JSONObject;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

public class WebSocketService extends Service {
    private static final String TAG = "WebSocketService";
    private static final String CHANNEL_ID = "fall_detection_channel";
    private static final int NOTIFICATION_ID = 1001;

    private WebSocket webSocket;
    private OkHttpClient client;
    private String wsUrl = "ws://10.0.2.2:8000/ws/notifications/"; //"ws://namujigi.pythonanywhere.com/ws/notifications/";
    private Handler reconnectHandler = new Handler(Looper.getMainLooper());
    private int reconnectDelay = 5000; // 5초 후 재연결

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();

        // Foreground Service로 실행 (Android 8.0+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification notification = new NotificationCompat.Builder(this, CHANNEL_ID)
                    .setContentTitle("낙상 감지 알림 대기 중")
                    .setContentText("실시간 알림을 받기 위해 연결 중입니다.")
                    .setSmallIcon(R.drawable.ic_launcher_foreground)
                    .setPriority(NotificationCompat.PRIORITY_LOW)
                    .build();
            startForeground(999, notification);
        }

        client = new OkHttpClient();
        connectWebSocket();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY; // 서비스가 종료되어도 재시작
    }

    private void connectWebSocket() {
        Request request = new Request.Builder()
                .url(wsUrl)
                .build();

        webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onOpen(WebSocket webSocket, Response response) {
                Log.d(TAG, "WebSocket connected");
                // Ping 메시지 주기적으로 전송 (연결 유지)
                startPingSchedule();
            }

            @Override
            public void onMessage(WebSocket webSocket, String text) {
                Log.d(TAG, "Message received: " + text);
                handleMessage(text);
            }

            @Override
            public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                Log.e(TAG, "WebSocket error: " + t.getMessage());
                scheduleReconnect();
            }

            @Override
            public void onClosed(WebSocket webSocket, int code, String reason) {
                Log.d(TAG, "WebSocket closed: " + reason);
                scheduleReconnect();
            }
        });
    }

    private void handleMessage(String message) {
        try {
            JSONObject json = new JSONObject(message);
            String type = json.optString("type", "");

            if ("fall_detected".equals(type)) {
                // 낙상 감지 알림
                String title = json.optString("title", "낙상 감지");
                String text = json.optString("text", "");
                int postId = json.optInt("post_id", 0);

                showNotification(title, text, postId);
            } else if ("connection_established".equals(type)) {
                Log.d(TAG, "Connection confirmed: " + json.optString("message"));
            }
        } catch (JSONException e) {
            Log.e(TAG, "JSON parse error: " + e.getMessage());
        }
    }

    private void showNotification(String title, String content, int postId) {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        intent.putExtra("post_id", postId);

        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle(title)
                .setContentText(content)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(content))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent);

        NotificationManager notificationManager =
                (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (notificationManager != null) {
            notificationManager.notify(NOTIFICATION_ID, builder.build());
        }

        Log.d(TAG, "Notification shown: " + title);
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            CharSequence name = "낙상 감지 알림";
            String description = "고령자 낙상 감지 시스템 알림";
            int importance = NotificationManager.IMPORTANCE_HIGH;
            NotificationChannel channel = new NotificationChannel(CHANNEL_ID, name, importance);
            channel.setDescription(description);

            NotificationManager notificationManager = getSystemService(NotificationManager.class);
            if (notificationManager != null) {
                notificationManager.createNotificationChannel(channel);
            }
        }
    }

    private void startPingSchedule() {
        reconnectHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                if (webSocket != null) {
                    try {
                        JSONObject ping = new JSONObject();
                        ping.put("type", "ping");
                        webSocket.send(ping.toString());
                        // 30초마다 ping 전송
                        reconnectHandler.postDelayed(this, 30000);
                    } catch (JSONException e) {
                        Log.e(TAG, "Ping error: " + e.getMessage());
                    }
                }
            }
        }, 30000);
    }

    private void scheduleReconnect() {
        reconnectHandler.postDelayed(new Runnable() {
            @Override
            public void run() {
                Log.d(TAG, "Attempting to reconnect...");
                connectWebSocket();
            }
        }, reconnectDelay);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (webSocket != null) {
            webSocket.close(1000, "Service destroyed");
        }
        reconnectHandler.removeCallbacksAndMessages(null);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}

package com.example.myapplication;

import android.Manifest;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.database.Cursor;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.AsyncTask;
import android.os.Build;
import android.os.Bundle;
import android.provider.MediaStore;
import android.view.View;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.List;

public class MainActivity extends AppCompatActivity {
    private static final int PICK_IMAGE = 1;
    private static final String CACHE_FILE_NAME = "blog_posts_cache.json";
    private static final String IMAGE_CACHE_DIR = "blog_images";

    TextView textView;
    String site_url = "http://10.0.2.2:8000"; // "https://namujigi.pythonanywhere.com";
    String token = "b20a99552f490b8dc9d9cd07c374569a967241ae"; //"cd8a230f97def11bf83669c8ca20fbe80f08a495";
    CloadPosts taskDownload;
    private RecyclerView recyclerView;
    private PostAdapter postAdapter;
    private List<BlogPost> blogPosts = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        textView = findViewById(R.id.textView);
        recyclerView = findViewById(R.id.recyclerView);
        recyclerView.setLayoutManager(new LinearLayoutManager(this));

        loadFromCache();

        // 알림 권한 요청 (Android 13+)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{Manifest.permission.POST_NOTIFICATIONS}, 101);
            }
        }

        // WebSocket Service 시작
        Intent serviceIntent = new Intent(this, WebSocketService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    public void onClickDownload(View v) {
        if (taskDownload != null && taskDownload.getStatus() == AsyncTask.Status.RUNNING) {
            taskDownload.cancel(true);
        }
        taskDownload = new CloadPosts();
        taskDownload.execute(site_url + "/api_root/Post/");
        Toast.makeText(getApplicationContext(), "동기화 중...", Toast.LENGTH_LONG).show();
    }


    // 캐시에 저장
    private void saveToCache(JSONArray jsonArray) {
        try {
            FileOutputStream fos = openFileOutput(CACHE_FILE_NAME, Context.MODE_PRIVATE);
            fos.write(jsonArray.toString().getBytes());
            fos.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // 캐시에서 로드
    private void loadFromCache() {
        try {
            FileInputStream fis = openFileInput(CACHE_FILE_NAME);
            InputStreamReader isr = new InputStreamReader(fis);
            BufferedReader br = new BufferedReader(isr);
            StringBuilder sb = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
            br.close();

            if (sb.length() > 0) {
                JSONArray cachedData = new JSONArray(sb.toString());
                displayPosts(cachedData);
                textView.setText("캐시에서 " + cachedData.length() + "개의 게시글을 불러왔습니다.");
            }
        } catch (IOException | JSONException e) {
            textView.setText("저장된 데이터가 없습니다. 동기화 버튼을 눌러주세요.");
        }
    }

    // 이미지를 로컬에 저장 (이미지는 사이즈가 크기에 따로 관리)
    private void saveImageToLocal(Bitmap bitmap, String fileName) {
        try {
            File dir = new File(getFilesDir(), IMAGE_CACHE_DIR);
            if (!dir.exists()) dir.mkdirs();

            File file = new File(dir, fileName);
            FileOutputStream fos = new FileOutputStream(file);
            bitmap.compress(Bitmap.CompressFormat.JPEG, 90, fos);
            fos.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    // 로컬에서 이미지 로드 (캐싱 데이터 로드 - 이미지)
    private Bitmap loadImageFromLocal(String fileName) {
        try {
            File file = new File(getFilesDir(), IMAGE_CACHE_DIR + "/" + fileName);
            if (file.exists()) {
                return BitmapFactory.decodeFile(file.getAbsolutePath());
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private void displayPosts(JSONArray aryJson) {
        blogPosts.clear();
        try {
            for (int i = 0; i < aryJson.length(); i++) {
                JSONObject postJson = aryJson.getJSONObject(i);

                int author = postJson.optInt("author", 0);
                String title = postJson.optString("title", "제목 없음");
                String text = postJson.optString("text", "");
                String created_date = postJson.optString("created_date", "");
                String published_date = postJson.optString("published_date", "");
                String imageUrl = postJson.optString("image", "");
                String videoUrl = postJson.optString("video", "");

                // 이미지 파일명 추출
                String imageFileName = imageUrl.substring(imageUrl.lastIndexOf("/") + 1);
                Bitmap imageBitmap = loadImageFromLocal(imageFileName);

                BlogPost post = new BlogPost(author, title, text, created_date,
                        published_date, imageUrl, imageBitmap, videoUrl);
                blogPosts.add(post);
            }

            postAdapter = new PostAdapter(blogPosts);
            recyclerView.setAdapter(postAdapter);

        } catch (JSONException e) {
            e.printStackTrace();
        }
    }

    private class CloadPosts extends AsyncTask<String, Void, JSONArray> {
        @Override
        protected JSONArray doInBackground(String... urls) {
            try {
                String apiUrl = urls[0];
                URL urlAPI = new URL(apiUrl);
                HttpURLConnection conn = (HttpURLConnection) urlAPI.openConnection();
                conn.setRequestProperty("Authorization", "Token " + token);
                conn.setRequestMethod("GET");
                conn.setConnectTimeout(5000);
                conn.setReadTimeout(5000);

                int responseCode = conn.getResponseCode();
                if (responseCode == HttpURLConnection.HTTP_OK) {
                    InputStream is = conn.getInputStream();
                    BufferedReader reader = new BufferedReader(new InputStreamReader(is));
                    StringBuilder result = new StringBuilder();
                    String line;
                    while ((line = reader.readLine()) != null) {
                        result.append(line);
                    }
                    is.close();

                    // Django REST Framework 페이지네이션 처리
                    JSONObject responseObj = new JSONObject(result.toString());
                    JSONArray aryJson = responseObj.getJSONArray("results");

                    // 이미지 다운로드 및 저장
                    for (int i = 0; i < aryJson.length(); i++) {
                        JSONObject postJson = aryJson.getJSONObject(i);
                        String imageUrl = postJson.optString("image", "");

                        if (imageUrl != null && !imageUrl.isEmpty() && !imageUrl.equals("null")) {
                            try {
                                URL myImageUrl = new URL(imageUrl);
                                HttpURLConnection imgConn = (HttpURLConnection) myImageUrl.openConnection();
                                InputStream imgStream = imgConn.getInputStream();
                                Bitmap imageBitmap = BitmapFactory.decodeStream(imgStream);
                                imgStream.close();

                                // 이미지 파일명 추출 및 저장
                                String imageFileName = imageUrl.substring(imageUrl.lastIndexOf("/") + 1);
                                saveImageToLocal(imageBitmap, imageFileName);

                            } catch (Exception e) {
                                e.printStackTrace();
                            }
                        }
                    }

                    conn.disconnect();
                    return aryJson;
                }
                conn.disconnect();
            } catch (IOException | JSONException e) {
                e.printStackTrace();
            }
            return null;
        }

        @Override
        protected void onPostExecute(JSONArray result) {
            if (result == null || result.length() == 0) {
                textView.setText("불러올 게시글이 없습니다.");
            } else {
                textView.setText(result.length() + "개의 게시글을 동기화했습니다.");
                saveToCache(result);
                displayPosts(result);
            }
        }
    }

}

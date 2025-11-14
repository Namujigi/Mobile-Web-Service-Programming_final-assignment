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
    String site_url = "https://namujigi.pythonanywhere.com";
    String token = "cd8a230f97def11bf83669c8ca20fbe80f08a495";
    CloadPosts taskDownload;
    UploadPost taskUpload;
    private Uri selectedImageUri = null;
    String[] permissions;
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
    }

    public void onClickDownload(View v) {
        if (taskDownload != null && taskDownload.getStatus() == AsyncTask.Status.RUNNING) {
            taskDownload.cancel(true);
        }
        taskDownload = new CloadPosts();
        taskDownload.execute(site_url + "/api_root/Post/");
        Toast.makeText(getApplicationContext(), "동기화 중...", Toast.LENGTH_LONG).show();
    }

    public void onClickUpload(View v) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions = new String[]{ Manifest.permission.READ_MEDIA_IMAGES };
        } else {
            permissions = new String[]{ Manifest.permission.READ_EXTERNAL_STORAGE };
        }

        if (ContextCompat.checkSelfPermission(this, permissions[0]) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, permissions, 100);
        } else {
            Intent intent = new Intent(Intent.ACTION_PICK);
            intent.setType("image/*");
            startActivityForResult(intent, PICK_IMAGE);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == 100) { // 100은 onClickUpload에서 요청한 코드
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                // 권한 승인됨
                Intent intent = new Intent(Intent.ACTION_PICK);
                intent.setType("image/*");
                startActivityForResult(intent, PICK_IMAGE);
            } else {
                // 권한 거부됨
                Toast.makeText(this, "이미지 접근 권한이 필요합니다.", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == PICK_IMAGE && resultCode == RESULT_OK && data != null) {
            selectedImageUri = data.getData();
            showUploadDialog();
        }
    }

    private void showUploadDialog() {
        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        View dialogView = getLayoutInflater().inflate(R.layout.dialog_upload, null);
        EditText etTitle = dialogView.findViewById(R.id.etTitle);
        EditText etText = dialogView.findViewById(R.id.etText);
        ImageView ivPreview = dialogView.findViewById(R.id.ivPreview);

        try {
            Bitmap bitmap = MediaStore.Images.Media.getBitmap(getContentResolver(), selectedImageUri);
            ivPreview.setImageBitmap(bitmap);
        } catch (IOException e) {
            e.printStackTrace();
        }

        builder.setView(dialogView);
        builder.setTitle("새 게시글 작성");
        builder.setPositiveButton("업로드", (dialog, which) -> {
            String title = etTitle.getText().toString().trim();
            String text = etText.getText().toString().trim();
            if (title.isEmpty() || text.isEmpty()) {
                Toast.makeText(this, "제목과 내용을 입력하세요", Toast.LENGTH_SHORT).show();
                return;
            }
            uploadPost(title, text);
        });
        builder.setNegativeButton("취소", null);
        builder.show();
    }

    private void uploadPost(String title, String text) {
        String imagePath = getPathFromUri(selectedImageUri);
        if (imagePath == null) {
            Toast.makeText(this, "이미지를 찾을 수 없습니다", Toast.LENGTH_SHORT).show();
            return;
        }

        if (taskUpload != null && taskUpload.getStatus() == AsyncTask.Status.RUNNING) {
            taskUpload.cancel(true);
        }
        taskUpload = new UploadPost();
        taskUpload.execute(title, text, imagePath);
        Toast.makeText(this, "업로드 중...", Toast.LENGTH_SHORT).show();
    }

    private String getPathFromUri(Uri contentUri) {
        String[] proj = {MediaStore.Images.Media.DATA};
        Cursor cursor = getContentResolver().query(contentUri, proj, null, null, null);
        if (cursor != null) {
            int column_index = cursor.getColumnIndexOrThrow(MediaStore.Images.Media.DATA);
            cursor.moveToFirst();
            String path = cursor.getString(column_index);
            cursor.close();
            return path;
        }
        return null;
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

                // 이미지 파일명 추출
                String imageFileName = imageUrl.substring(imageUrl.lastIndexOf("/") + 1);
                Bitmap imageBitmap = loadImageFromLocal(imageFileName);

                BlogPost post = new BlogPost(author, title, text, created_date,
                        published_date, imageUrl, imageBitmap);
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

                    JSONArray aryJson = new JSONArray(result.toString());

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

    private class UploadPost extends AsyncTask<String, Void, Boolean> {
        @Override
        protected Boolean doInBackground(String... params) {
            String title = params[0];
            String text = params[1];
            String imagePath = params[2];
            String lineEnd = "\r\n";
            String twoHyphens = "--";
            String boundary = "*****" + System.currentTimeMillis() + "*****";

            try {
                File imageFile = new File(imagePath);
                FileInputStream fileInputStream = new FileInputStream(imageFile);

                URL url = new URL(site_url + "/api_root/Post/");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setDoInput(true);
                conn.setDoOutput(true);
                conn.setUseCaches(false);
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Connection", "Keep-Alive");
                conn.setRequestProperty("Authorization", "Token " + token);
                conn.setRequestProperty("Content-Type", "multipart/form-data;boundary=" + boundary);

                DataOutputStream dos = new DataOutputStream(conn.getOutputStream());

                dos.writeBytes(twoHyphens + boundary + lineEnd);
                dos.writeBytes("Content-Disposition: form-data; name=\"title\"" + lineEnd);
                dos.writeBytes(lineEnd);
                dos.writeBytes(title);
                dos.writeBytes(lineEnd);

                dos.writeBytes(twoHyphens + boundary + lineEnd);
                dos.writeBytes("Content-Disposition: form-data; name=\"text\"" + lineEnd);
                dos.writeBytes(lineEnd);
                dos.writeBytes(text);
                dos.writeBytes(lineEnd);

                dos.writeBytes(twoHyphens + boundary + lineEnd);
                dos.writeBytes("Content-Disposition: form-data; name=\"author\"" + lineEnd);
                dos.writeBytes(lineEnd);
                dos.writeBytes("1");
                dos.writeBytes(lineEnd);

                dos.writeBytes(twoHyphens + boundary + lineEnd);
                dos.writeBytes("Content-Disposition: form-data; name=\"image\";filename=\"" +
                        imageFile.getName() + "\"" + lineEnd);
                dos.writeBytes("Content-Type: image/jpeg" + lineEnd);
                dos.writeBytes(lineEnd);

                int bytesAvailable = fileInputStream.available();
                int maxBufferSize = 1024 * 1024;
                int bufferSize = Math.min(bytesAvailable, maxBufferSize);
                byte[] buffer = new byte[bufferSize];
                int bytesRead = fileInputStream.read(buffer, 0, bufferSize);

                while (bytesRead > 0) {
                    dos.write(buffer, 0, bufferSize);
                    bytesAvailable = fileInputStream.available();
                    bufferSize = Math.min(bytesAvailable, maxBufferSize);
                    bytesRead = fileInputStream.read(buffer, 0, bufferSize);
                }

                dos.writeBytes(lineEnd);
                dos.writeBytes(twoHyphens + boundary + twoHyphens + lineEnd);

                fileInputStream.close();
                dos.flush();
                dos.close();

                int responseCode = conn.getResponseCode();
                return (responseCode == HttpURLConnection.HTTP_OK ||
                        responseCode == HttpURLConnection.HTTP_CREATED);

            } catch (Exception e) {
                e.printStackTrace();
                return false;
            }
        }

        @Override
        protected void onPostExecute(Boolean success) {
            if (success) {
                Toast.makeText(MainActivity.this, "업로드 성공!", Toast.LENGTH_SHORT).show();
                onClickDownload(null);
            } else {
                Toast.makeText(MainActivity.this, "업로드 실패", Toast.LENGTH_SHORT).show();
            }
        }
    }
}

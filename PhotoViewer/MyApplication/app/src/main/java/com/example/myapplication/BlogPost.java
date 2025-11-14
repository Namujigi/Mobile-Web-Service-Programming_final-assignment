package com.example.myapplication;

import android.graphics.Bitmap;

public class BlogPost {
    private int author;
    private String title;
    private String text;
    private String created_date;
    private String published_date;
    private String imageUrl;
    private Bitmap imageBitmap;
    private boolean imageVisible;

    public BlogPost(int author, String title, String text, String created_date,
                    String published_date, String imageUrl, Bitmap imageBitmap) {
        this.author = author;
        this.title = title;
        this.text = text;
        this.created_date = created_date;
        this.published_date = published_date;
        this.imageUrl = imageUrl;
        this.imageBitmap = imageBitmap;
        this.imageVisible = true; // 초기 상태: 보임
    }

    // Getters and Setters
    public int getAuthor() { return author; }
    public void setAuthor(int author) { this.author = author; }

    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }

    public String getText() { return text; }
    public void setText(String text) { this.text = text; }

    public String getCreated_date() { return created_date; }
    public void setCreated_date(String created_date) { this.created_date = created_date; }

    public String getPublished_date() { return published_date; }
    public void setPublished_date(String published_date) { this.published_date = published_date; }

    public String getImageUrl() { return imageUrl; }
    public void setImageUrl(String imageUrl) { this.imageUrl = imageUrl; }

    public Bitmap getImageBitmap() { return imageBitmap; }
    public void setImageBitmap(Bitmap imageBitmap) { this.imageBitmap = imageBitmap; }

    public boolean isImageVisible() { return imageVisible; }
    public void setImageVisible(boolean imageVisible) { this.imageVisible = imageVisible; }
}

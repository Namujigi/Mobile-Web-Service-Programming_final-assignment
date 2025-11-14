package com.example.myapplication;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class PostAdapter extends RecyclerView.Adapter<PostAdapter.PostViewHolder> {
    private List<BlogPost> postList;

    public PostAdapter(List<BlogPost> postList) {
        this.postList = postList;
    }

    @Override
    public PostViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_post, parent, false);
        return new PostViewHolder(view);
    }

    @Override
    public void onBindViewHolder(PostViewHolder holder, int position) {
        BlogPost post = postList.get(position);

        holder.tvTitle.setText(post.getTitle());
        holder.tvText.setText(post.getText());
        holder.tvDate.setText("작성일: " + formatDate(post.getCreated_date()));

        if (post.getImageBitmap() != null) {
            holder.imageView.setImageBitmap(post.getImageBitmap());
            holder.imageView.setVisibility(post.isImageVisible() ? View.VISIBLE : View.GONE);
            holder.btnToggleImage.setVisibility(View.VISIBLE);
            holder.btnToggleImage.setText(post.isImageVisible() ? "이미지 숨기기" : "이미지 보이기");
        } else {
            holder.imageView.setVisibility(View.GONE);
            holder.btnToggleImage.setVisibility(View.GONE);
        }

        holder.btnToggleImage.setOnClickListener(v -> {
            post.setImageVisible(!post.isImageVisible());
            notifyItemChanged(position);
        });
    }

    @Override
    public int getItemCount() {
        return postList.size();
    }

    private String formatDate(String dateString) {
        if (dateString == null || dateString.isEmpty()) return "";
        try {
            // 2025-10-09T04:14:10+09:00 형식을 간단하게 표시
            return dateString.substring(0, 10) + " " + dateString.substring(11, 19);
        } catch (Exception e) {
            return dateString;
        }
    }

    public static class PostViewHolder extends RecyclerView.ViewHolder {
        TextView tvTitle, tvText, tvDate;
        ImageView imageView;
        Button btnToggleImage;

        public PostViewHolder(View itemView) {
            super(itemView);
            tvTitle = itemView.findViewById(R.id.tvTitle);
            tvText = itemView.findViewById(R.id.tvText);
            tvDate = itemView.findViewById(R.id.tvDate);
            imageView = itemView.findViewById(R.id.imageViewItem);
            btnToggleImage = itemView.findViewById(R.id.btnToggleImage);
        }
    }
}

package com.example.myapplication;

import android.net.Uri;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.media3.common.MediaItem;
import androidx.media3.common.PlaybackException;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;
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

        // 기존 플레이어 해제
        holder.releasePlayer();

        // 동영상 표시 및 재생 (ExoPlayer 사용)
        if (post.getVideoUrl() != null && !post.getVideoUrl().isEmpty()
                && !post.getVideoUrl().equals("null")) {
            Log.d("PostAdapter", "Video URL: " + post.getVideoUrl());
            holder.playerView.setVisibility(View.VISIBLE);
            holder.tvVideoLabel.setVisibility(View.VISIBLE);

            // ExoPlayer 초기화
            holder.player = new ExoPlayer.Builder(holder.itemView.getContext()).build();
            holder.playerView.setPlayer(holder.player);

            // MediaItem 생성 및 설정
            MediaItem mediaItem = MediaItem.fromUri(post.getVideoUrl());
            holder.player.setMediaItem(mediaItem);
            holder.player.prepare();

            // 에러 리스너 추가
            holder.player.addListener(new Player.Listener() {
                @Override
                public void onPlayerError(PlaybackException error) {
                    Log.e("PostAdapter", "ExoPlayer error: " + error.getMessage());
                    Log.e("PostAdapter", "Error URL: " + post.getVideoUrl());
                }

                @Override
                public void onPlaybackStateChanged(int playbackState) {
                    if (playbackState == Player.STATE_READY) {
                        Log.d("PostAdapter", "Video ready to play");
                    }
                }
            });

            // 자동 재생 비활성화
            holder.player.setPlayWhenReady(false);
        } else {
            Log.d("PostAdapter", "No video URL or invalid: " + post.getVideoUrl());
            holder.playerView.setVisibility(View.GONE);
            holder.tvVideoLabel.setVisibility(View.GONE);
        }
    }

    @Override
    public int getItemCount() {
        return postList.size();
    }

    @Override
    public void onViewRecycled(PostViewHolder holder) {
        super.onViewRecycled(holder);
        holder.releasePlayer();
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
        TextView tvTitle, tvText, tvDate, tvVideoLabel;
        ImageView imageView;
        Button btnToggleImage;
        PlayerView playerView;
        ExoPlayer player;

        public PostViewHolder(View itemView) {
            super(itemView);
            tvTitle = itemView.findViewById(R.id.tvTitle);
            tvText = itemView.findViewById(R.id.tvText);
            tvDate = itemView.findViewById(R.id.tvDate);
            imageView = itemView.findViewById(R.id.imageViewItem);
            btnToggleImage = itemView.findViewById(R.id.btnToggleImage);
            playerView = itemView.findViewById(R.id.playerViewItem);
            tvVideoLabel = itemView.findViewById(R.id.tvVideoLabel);
        }

        public void releasePlayer() {
            if (player != null) {
                player.release();
                player = null;
            }
        }
    }
}

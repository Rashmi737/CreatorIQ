from typing import Any


class GrowthTrendService:
    def follower_growth_velocity(self, points: list[dict[str, Any]]) -> float:
        if len(points) < 2:
            return 0.0
        return round((points[-1].get("followers", 0) - points[0].get("followers", 0)) / (len(points) - 1), 2)

    def trends(self, points: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "points": points,
            "follower_growth_velocity": self.follower_growth_velocity(points),
            "reach_change": (points[-1].get("reach", 0) - points[0].get("reach", 0)) if points else 0,
            "hashtags": [
                {"hashtag": "#creatorlife", "performance": 78},
                {"hashtag": "#behindthescenes", "performance": 64},
            ],
        }

    def extract_hashtags(self, posts: list[dict[str, Any]]) -> dict[str, Any]:
        """Extract and score hashtags from posts."""
        hashtag_stats = {}
        for post in posts:
            hashtags = post.get("hashtags", [])
            if isinstance(hashtags, str):
                hashtags = hashtags.split()
            
            for tag in hashtags:
                if tag not in hashtag_stats:
                    hashtag_stats[tag] = {"reach": 0, "engagement": 0, "count": 0}
                
                hashtag_stats[tag]["reach"] += post.get("reach", post.get("views", 0))
                interactions = post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)
                hashtag_stats[tag]["engagement"] += interactions
                hashtag_stats[tag]["count"] += 1
        
        # Convert to list and sort by reach
        result = [
            {
                "hashtag": tag,
                "reach": stats["reach"],
                "engagement": stats["engagement"],
                "avg_engagement_per_post": round(stats["engagement"] / stats["count"], 2),
                "posts": stats["count"],
            }
            for tag, stats in hashtag_stats.items()
        ]
        return {"hashtags": sorted(result, key=lambda x: x["reach"], reverse=True)}

    def forecast_growth(self, historical_points: list[dict[str, Any]], forecast_days: int = 7) -> dict[str, Any]:
        """Forecast follower and reach growth using linear projection."""
        if len(historical_points) < 2:
            return {"forecast": [], "error": "Insufficient historical data"}
        
        # Calculate daily velocity
        follower_velocity = (historical_points[-1].get("followers", 0) - historical_points[0].get("followers", 0)) / (len(historical_points) - 1)
        reach_velocity = (historical_points[-1].get("reach", 0) - historical_points[0].get("reach", 0)) / (len(historical_points) - 1)
        
        # Project forward
        forecast = []
        for i in range(1, forecast_days + 1):
            forecast.append({
                "day": i,
                "followers": round(historical_points[-1].get("followers", 0) + follower_velocity * i),
                "reach": round(historical_points[-1].get("reach", 0) + reach_velocity * i),
            })
        
        return {
            "forecast": forecast,
            "velocity": {
                "followers_per_day": round(follower_velocity, 2),
                "reach_per_day": round(reach_velocity, 2),
            },
            "forecast_days": forecast_days,
        }

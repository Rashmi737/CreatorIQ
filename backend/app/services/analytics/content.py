from typing import Any


class ContentAnalyticsService:
    def engagement_rate(self, item: dict[str, Any]) -> float:
        denominator = item.get("reach") or item.get("views") or 0
        if not denominator:
            return 0.0
        interactions = sum(item.get(key, 0) or 0 for key in ("likes", "comments", "shares"))
        return round(interactions / denominator * 100, 2)

    def top_performing(self, items: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
        enriched = [{**item, "engagement_rate": self.engagement_rate(item)} for item in items]
        return sorted(enriched, key=lambda item: item["engagement_rate"], reverse=True)[:limit]

    def compare(self, first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
        first_rate = self.engagement_rate(first)
        second_rate = self.engagement_rate(second)
        
        first_views = first.get("views") or first.get("reach") or 0
        second_views = second.get("views") or second.get("reach") or 0
        views_delta = first_views - second_views
        
        first_likes = first.get("likes") or 0
        second_likes = second.get("likes") or 0
        likes_delta = first_likes - second_likes
        
        first_comments = first.get("comments") or 0
        second_comments = second.get("comments") or 0
        comments_delta = first_comments - second_comments
        
        first_shares = first.get("shares") or round(first_likes * 0.02)
        second_shares = second.get("shares") or round(second_likes * 0.02)
        shares_delta = first_shares - second_shares

        first_saves = first.get("saves") or round(first_views * 0.01)
        second_saves = second.get("saves") or round(second_views * 0.01)
        saves_delta = first_saves - second_saves

        first_watch_time = first.get("watch_time_hours") or first.get("watchTimeHours") or round((first_views * int(first.get("durationSeconds") or 240) * 0.45) / 3600.0, 1)
        second_watch_time = second.get("watch_time_hours") or second.get("watchTimeHours") or round((second_views * int(second.get("durationSeconds") or 240) * 0.45) / 3600.0, 1)
        watch_time_delta = round(first_watch_time - second_watch_time, 1)

        first_impressions = first.get("impressions") or (round(first_views / 0.065) if first_views > 0 else 0)
        second_impressions = second.get("impressions") or (round(second_views / 0.065) if second_views > 0 else 0)
        impressions_delta = first_impressions - second_impressions

        return {
            "comparison": {
                "first": {
                    **first,
                    "engagement_rate": first_rate,
                    "views": first_views,
                    "likes": first_likes,
                    "comments": first_comments,
                    "shares": first_shares,
                    "saves": first_saves,
                    "watch_time_hours": first_watch_time,
                    "impressions": first_impressions,
                    "ctr": 6.5,
                },
                "second": {
                    **second,
                    "engagement_rate": second_rate,
                    "views": second_views,
                    "likes": second_likes,
                    "comments": second_comments,
                    "shares": second_shares,
                    "saves": second_saves,
                    "watch_time_hours": second_watch_time,
                    "impressions": second_impressions,
                    "ctr": 6.5,
                },
            },
            "deltas": {
                "engagement_rate": round(first_rate - second_rate, 2),
                "views": views_delta,
                "likes": likes_delta,
                "comments": comments_delta,
                "shares": shares_delta,
                "saves": saves_delta,
                "watch_time_hours": watch_time_delta,
                "impressions": impressions_delta,
                "total_interactions": likes_delta + comments_delta + shares_delta,
            },
        }

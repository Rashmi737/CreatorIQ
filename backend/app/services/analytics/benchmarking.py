import csv
import io
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.social import PlatformAccount, SocialContent


PLATFORM_METADATA = {
    "youtube": {"label": "YouTube", "icon": "▶", "color": "#ef4444", "audience_label": "Subscribers"},
    "github": {"label": "GitHub", "icon": "🐙", "color": "#10b981", "audience_label": "Followers / Stars"},
    "linkedin": {"label": "LinkedIn", "icon": "💼", "color": "#0284c7", "audience_label": "Connections / Followers"},
    "instagram": {"label": "Instagram", "icon": "📷", "color": "#ec4899", "audience_label": "Followers"},
    "facebook": {"label": "Facebook", "icon": "🌐", "color": "#3b82f6", "audience_label": "Followers / Likes"},
    "twitter": {"label": "X (Twitter)", "icon": "𝕏", "color": "#0f172a", "audience_label": "Followers"},
    "x": {"label": "X (Twitter)", "icon": "𝕏", "color": "#0f172a", "audience_label": "Followers"},
}


class BenchmarkingAnalyticsService:
    """
    Computes authentic cross-platform benchmarks, creator intelligence recommendations,
    and export summaries strictly derived from SQLite PlatformAccount and SocialContent records.
    Zero-Mock Rule: NEVER fabricate synthetic fallbacks or demographic percentages.
    """

    def get_workspace_accounts(self, user_id: str | None, db: Session) -> list[PlatformAccount]:
        """Fetch platform accounts for a specific user, or fallback to workspace accounts if unauthenticated."""
        query = select(PlatformAccount)
        accounts: list[PlatformAccount] = []
        if user_id:
            accounts = list(db.scalars(query.where(PlatformAccount.user_id == str(user_id))).all())

        if not accounts:
            accounts = list(db.scalars(query.order_by(PlatformAccount.updated_at.desc())).all())

        # Deduplicate accounts by (platform_name, platform_user_id) keeping the most recent
        seen: set[tuple[str, str]] = set()
        deduped: list[PlatformAccount] = []
        for acc in accounts:
            key = (acc.platform_name.lower().strip(), acc.platform_user_id.lower().strip())
            if key not in seen:
                seen.add(key)
                deduped.append(acc)
        return deduped

    def compute_cross_platform_benchmarks(self, user_id: str | None, db: Session) -> dict[str, Any]:
        """
        Calculates authentic cross-platform metrics across all connected platform profiles:
        - Total verified audience scale
        - Platform share distribution (% of audience per platform)
        - Engagement efficiency ratio strictly from live records
        - Velocity ranking (scale & engagement density)
        """
        accounts = self.get_workspace_accounts(user_id, db)

        if not accounts:
            return {
                "workspace_scale": {
                    "total_audience": 0,
                    "total_views": 0,
                    "total_posts_tracked": 0,
                    "total_interactions": 0,
                    "connected_platforms_count": 0,
                    "active_accounts_count": 0,
                },
                "connected_platforms": [],
                "platform_share_distribution": [],
                "engagement_efficiency": [],
                "velocity_ranking": [],
                "accounts_matrix": [],
                "creator_recommendations": self.generate_creator_recommendations(user_id, db, benchmarks=None),
                "zero_mock_attestation": {
                    "synthetic_data_present": False,
                    "data_source": "SQLite PlatformAccount & SocialContent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            }

        total_audience = 0
        total_views = 0
        total_posts_tracked = 0
        total_interactions = 0

        accounts_data: list[dict[str, Any]] = []

        for acc in accounts:
            plat = acc.platform_name.lower().strip()
            if plat == "tiktok":
                continue
            followers = int(acc.subscribers_count or 0)
            views = int(acc.total_views or 0)
            meta = PLATFORM_METADATA.get(plat, {"label": plat.title(), "icon": "🔗", "color": "#64748b", "audience_label": "Followers"})

            # Query real social contents for this account
            contents: list[SocialContent] = list(
                db.scalars(
                    select(SocialContent).where(
                        (SocialContent.platform_account_id == acc.id)
                        | (
                            (SocialContent.platform == plat)
                            & (SocialContent.user_id == acc.user_id)
                        )
                    )
                ).all()
            )

            # Deduplicate contents by external_id
            seen_items: set[str] = set()
            unique_contents: list[SocialContent] = []
            for c in contents:
                if c.external_id not in seen_items:
                    seen_items.add(c.external_id)
                    unique_contents.append(c)

            posts_count = len(unique_contents) if unique_contents else int(acc.video_count or 0)
            likes_sum = sum(int(c.likes or 0) for c in unique_contents)
            comments_sum = sum(int(c.comments or 0) for c in unique_contents)
            shares_sum = sum(int(c.shares or 0) for c in unique_contents)
            item_interactions = likes_sum + comments_sum

            # Strict Zero-Mock efficiency ratio:
            # (average interaction per post / follower count) * 100
            # If 0 posts or 0 followers, strictly 0.0 (no synthetic estimates)
            if followers > 0 and len(unique_contents) > 0:
                avg_inter_per_post = item_interactions / len(unique_contents)
                efficiency_ratio = round((avg_inter_per_post / followers) * 100, 2)
            elif len(unique_contents) > 0:
                # Average individual engagement rate if followers is 0/private
                effs = [float(c.engagement_rate or 0.0) for c in unique_contents if c.engagement_rate]
                efficiency_ratio = round(sum(effs) / len(effs), 2) if effs else 0.0
            else:
                efficiency_ratio = 0.0

            total_audience += followers
            total_views += views
            total_posts_tracked += len(unique_contents)
            total_interactions += item_interactions

            accounts_data.append({
                "account_id": acc.id,
                "platform": plat,
                "platform_label": meta["label"],
                "icon": meta["icon"],
                "color": meta["color"],
                "audience_label": meta["audience_label"],
                "handle": acc.platform_user_id,
                "display_name": acc.channel_title or acc.platform_user_id,
                "avatar_url": acc.avatar_url,
                "followers": followers,
                "views": views,
                "posts_count": posts_count,
                "tracked_items_count": len(unique_contents),
                "likes_sum": likes_sum,
                "comments_sum": comments_sum,
                "shares_sum": shares_sum,
                "interactions_sum": item_interactions,
                "efficiency_ratio": efficiency_ratio,
                "ingestion_mode": acc.scopes or "public_web",
                "last_synced": acc.updated_at.isoformat() if acc.updated_at else datetime.now(timezone.utc).isoformat(),
            })

        # Platform Share Distribution
        platform_groups: dict[str, dict[str, Any]] = {}
        for item in accounts_data:
            p = item["platform"]
            if p not in platform_groups:
                platform_groups[p] = {
                    "platform": p,
                    "label": item["platform_label"],
                    "icon": item["icon"],
                    "color": item["color"],
                    "audience": 0,
                    "views": 0,
                    "interactions": 0,
                    "posts_count": 0,
                    "accounts_count": 0,
                    "efficiency_ratios": [],
                }
            g = platform_groups[p]
            g["audience"] += item["followers"]
            g["views"] += item["views"]
            g["interactions"] += item["interactions_sum"]
            g["posts_count"] += item["tracked_items_count"]
            g["accounts_count"] += 1
            if item["efficiency_ratio"] > 0:
                g["efficiency_ratios"].append(item["efficiency_ratio"])

        platform_share_distribution = []
        for p, g in platform_groups.items():
            share_pct = round((g["audience"] / total_audience) * 100, 1) if total_audience > 0 else 0.0
            avg_eff = round(sum(g["efficiency_ratios"]) / len(g["efficiency_ratios"]), 2) if g["efficiency_ratios"] else 0.0
            platform_share_distribution.append({
                "platform": p,
                "label": g["label"],
                "icon": g["icon"],
                "color": g["color"],
                "audience": g["audience"],
                "share_percentage": share_pct,
                "views": g["views"],
                "interactions": g["interactions"],
                "posts_count": g["posts_count"],
                "accounts_count": g["accounts_count"],
                "avg_efficiency_ratio": avg_eff,
            })

        # Sort share distribution by audience descending
        platform_share_distribution.sort(key=lambda x: x["audience"], reverse=True)

        # Velocity Ranking (Follower Scale Leaderboard)
        velocity_ranking = sorted(
            accounts_data,
            key=lambda x: (x["followers"], x["efficiency_ratio"], x["views"]),
            reverse=True,
        )

        # Engagement Efficiency Ranking
        engagement_efficiency = sorted(
            platform_share_distribution,
            key=lambda x: (x["avg_efficiency_ratio"], x["interactions"]),
            reverse=True,
        )

        benchmarks_summary = {
            "workspace_scale": {
                "total_audience": total_audience,
                "total_views": total_views,
                "total_posts_tracked": total_posts_tracked,
                "total_interactions": total_interactions,
                "connected_platforms_count": len(platform_groups),
                "active_accounts_count": len(accounts_data),
            },
            "connected_platforms": list(platform_groups.keys()),
            "platform_share_distribution": platform_share_distribution,
            "engagement_efficiency": engagement_efficiency,
            "velocity_ranking": velocity_ranking,
            "accounts_matrix": accounts_data,
            "zero_mock_attestation": {
                "synthetic_data_present": False,
                "data_source": "SQLite PlatformAccount & SocialContent",
                "verified_records_count": len(accounts_data),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }

        benchmarks_summary["creator_recommendations"] = self.generate_creator_recommendations(
            user_id, db, benchmarks=benchmarks_summary
        )

        return benchmarks_summary

    def generate_creator_recommendations(
        self, user_id: str | None, db: Session, benchmarks: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Analyzes authentic post frequency, text headline length, and platform engagement efficiency
        to generate data-driven creator action items.
        Strict Zero-Mock: Derived entirely from real numbers in DB.
        """
        if benchmarks is None:
            accounts = self.get_workspace_accounts(user_id, db)
            if not accounts:
                return [
                    {
                        "category": "Setup",
                        "badge": "Connect Channels",
                        "title": "Build your unified creator footprint",
                        "description": "Analyze and connect your accounts across YouTube, GitHub, LinkedIn, Instagram, or Facebook in Content Analytics to unlock cross-platform benchmarks and actionable intelligence.",
                        "impact": "High",
                        "priority": 1,
                    }
                ]
            benchmarks = self.compute_cross_platform_benchmarks(user_id, db)

        accounts_matrix = benchmarks.get("accounts_matrix", [])
        platform_shares = benchmarks.get("platform_share_distribution", [])
        total_audience = benchmarks.get("workspace_scale", {}).get("total_audience", 0)

        if not accounts_matrix:
            return [
                {
                    "category": "Setup",
                    "badge": "Workspace Initializing",
                    "title": "No platform accounts recorded yet",
                    "description": "Search public creator profiles in Content Analytics or connect accounts via the Social Media Hub to compute live benchmarks.",
                    "impact": "High",
                    "priority": 1,
                }
            ]

        recommendations: list[dict[str, Any]] = []

        # 1. Audience Concentration Recommendation
        if platform_shares:
            top_plat = platform_shares[0]
            if top_plat["share_percentage"] >= 50.0 and len(platform_shares) > 1:
                recommendations.append({
                    "category": "Audience Strategy",
                    "badge": "Concentration Risk",
                    "title": f"High Audience Weight in {top_plat['label']} ({top_plat['share_percentage']}%)",
                    "description": f"Over half of your verified reach ({top_plat['audience']:,} {top_plat['label']} followers) sits on one platform. Funnel followers to your other connected profiles to build platform resilience.",
                    "impact": "High",
                    "priority": 1,
                })
            elif len(platform_shares) == 1:
                recommendations.append({
                    "category": "Expansion",
                    "badge": "Multi-Platform Growth",
                    "title": f"Expand beyond {top_plat['label']}",
                    "description": f"You have 1 connected channel with {top_plat['audience']:,} audience. Adding your professional presence (LinkedIn) or developer footprint (GitHub) increases sponsor valuation.",
                    "impact": "Medium",
                    "priority": 2,
                })
            else:
                recommendations.append({
                    "category": "Audience Balance",
                    "badge": "Diversified Reach",
                    "title": f"Well-distributed footprint across {len(platform_shares)} platforms",
                    "description": f"Your audience is healthy and distributed across {', '.join([p['label'] for p in platform_shares])}. Lead platform is {top_plat['label']} with {top_plat['share_percentage']}% share.",
                    "impact": "Low",
                    "priority": 3,
                })

        # 2. GitHub Developer Velocity Intelligence
        github_acc = next((a for a in accounts_matrix if a["platform"] == "github"), None)
        if github_acc:
            stars = github_acc["views"]  # views stores total stars for github
            recommendations.append({
                "category": "Technical Authority",
                "badge": "GitHub Open Source",
                "title": f"GitHub developer velocity leads with {stars:,} stars",
                "description": f"Account @{github_acc['handle']} showcases {stars:,} stargazers across repositories. Highlight this open-source credibility in technical sponsor pitches and developer advocacy.",
                "impact": "High",
                "priority": 2,
            })

        # 3. Engagement Density Leader
        highest_eff_plat = max(platform_shares, key=lambda x: x.get("avg_efficiency_ratio", 0.0), default=None)
        if highest_eff_plat and highest_eff_plat.get("avg_efficiency_ratio", 0.0) > 0:
            recommendations.append({
                "category": "Engagement Velocity",
                "badge": f"{highest_eff_plat['label']} Outperformer",
                "title": f"{highest_eff_plat['label']} delivers top interaction density ({highest_eff_plat['avg_efficiency_ratio']:.2f}%)",
                "description": f"Your audience on {highest_eff_plat['label']} engages with higher proportional comments and likes. Prioritize conversational hooks and community replies on this channel.",
                "impact": "Medium",
                "priority": 3,
            })

        # 4. Content Headline & Length Analysis (Strict Zero-Mock from DB)
        content_items: list[SocialContent] = list(db.scalars(select(SocialContent).limit(50)).all())
        if content_items:
            titles = [c.title for c in content_items if c.title]
            if titles:
                avg_title_len = round(sum(len(t) for t in titles) / len(titles))
                question_titles = [t for t in titles if "?" in t]
                q_ratio = round((len(question_titles) / len(titles)) * 100)

                if q_ratio > 20:
                    recommendations.append({
                        "category": "Content Optimization",
                        "badge": "Headline Hook",
                        "title": f"Question-driven titles ({q_ratio}% of tracked posts) drive curiosity",
                        "description": f"Content titles average {avg_title_len} characters. Asking questions directly stimulates discussion and boosts algorithmic comment signals.",
                        "impact": "Medium",
                        "priority": 4,
                    })
                else:
                    recommendations.append({
                        "category": "Content Optimization",
                        "badge": "Title Strategy",
                        "title": f"Tested title length averages {avg_title_len} characters",
                        "description": "Front-load primary keywords in the first 40 characters for mobile display, and test incorporating curiosity questions to stimulate comment sections.",
                        "impact": "Low",
                        "priority": 4,
                    })

        # 5. Media Kit / Sponsor Deck Ready
        recommendations.append({
            "category": "Monetization",
            "badge": "Sponsor Ready",
            "title": f"Total verified footprint: {total_audience:,} audience members",
            "description": f"Verified multi-platform scale across {len(platform_shares)} platforms provides transparent metrics for brand deals. Download your authentic workspace CSV or Sponsor Deck JSON below.",
            "impact": "High",
            "priority": 5,
        })

        return recommendations

    def generate_workspace_csv(self, user_id: str | None, db: Session) -> str:
        """
        Generates an RFC 4180 compliant CSV string containing all authentic ingested profiles
        and live performance indicators. Zero mock records.
        """
        benchmarks = self.compute_cross_platform_benchmarks(user_id, db)
        accounts_matrix = benchmarks.get("accounts_matrix", [])

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Header row
        writer.writerow([
            "Platform",
            "Handle",
            "Display Name",
            "Followers / Subscribers",
            "Total Views / Stars",
            "Tracked Content Items",
            "Total Likes",
            "Total Comments",
            "Engagement Efficiency (%)",
            "Ingestion Mode",
            "Last Synced (UTC)",
        ])

        for a in accounts_matrix:
            writer.writerow([
                a.get("platform_label") or a.get("platform", "").title(),
                f"@{a.get('handle', '')}",
                a.get("display_name", ""),
                a.get("followers", 0),
                a.get("views", 0),
                a.get("tracked_items_count", 0),
                a.get("likes_sum", 0),
                a.get("comments_sum", 0),
                f"{a.get('efficiency_ratio', 0.0):.2f}%",
                a.get("ingestion_mode", "public_web"),
                a.get("last_synced", ""),
            ])

        return output.getvalue()

    def generate_sponsor_report(self, user_id: str | None, db: Session) -> dict[str, Any]:
        """
        Returns a clean, structured JSON report formatted for creator media kits,
        sponsorship pitches, and brand partnership decks.
        """
        benchmarks = self.compute_cross_platform_benchmarks(user_id, db)
        scale = benchmarks.get("workspace_scale", {})
        accounts = benchmarks.get("accounts_matrix", [])

        # Find top performing content items across all accounts
        content_items: list[SocialContent] = list(
            db.scalars(
                select(SocialContent).order_by(SocialContent.views.desc(), SocialContent.likes.desc()).limit(10)
            ).all()
        )

        top_assets = [
            {
                "title": c.title,
                "platform": c.platform.title(),
                "views": c.views,
                "likes": c.likes,
                "comments": c.comments,
                "engagement_rate": f"{c.engagement_rate:.1f}%",
                "published_at": c.published_at.isoformat() if c.published_at else None,
            }
            for c in content_items
        ]

        return {
            "creator_media_kit": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "verified_total_reach": scale.get("total_audience", 0),
                "total_views_impressions": scale.get("total_views", 0),
                "connected_platforms_count": scale.get("connected_platforms_count", 0),
                "active_profiles_count": scale.get("active_accounts_count", 0),
                "total_posts_monitored": scale.get("total_posts_tracked", 0),
                "platform_distribution": benchmarks.get("platform_share_distribution", []),
                "verified_profiles": [
                    {
                        "platform": a.get("platform_label"),
                        "handle": a.get("handle"),
                        "name": a.get("display_name"),
                        "audience": a.get("followers"),
                        "views_or_stars": a.get("views"),
                        "efficiency_rate": f"{a.get('efficiency_ratio', 0.0):.2f}%",
                        "ingestion_mode": a.get("ingestion_mode"),
                    }
                    for a in accounts
                ],
                "top_performing_assets": top_assets,
                "creator_intelligence_insights": benchmarks.get("creator_recommendations", []),
                "zero_mock_attestation": {
                    "verified": True,
                    "notice": "All metrics and statistics are derived from authentic ingested platform records via CreatorIQ. Zero synthetic or simulated data.",
                },
            }
        }

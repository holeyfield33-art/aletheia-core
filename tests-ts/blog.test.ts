import { describe, expect, test } from "vitest";
import { BLOG_POSTS, getPostBySlug } from "@/app/blog/_posts";

describe("blog posts", () => {
  test("getPostBySlug returns post for known slug", () => {
    const knownSlug = BLOG_POSTS[0]?.slug;
    expect(knownSlug).toBeTruthy();

    const post = getPostBySlug(knownSlug as string);
    expect(post).toBeDefined();
    expect(post?.slug).toBe(knownSlug);
  });

  test("getPostBySlug returns undefined for unknown slug", () => {
    const post = getPostBySlug("does-not-exist");
    expect(post).toBeUndefined();
  });
});

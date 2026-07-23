<?xml version="1.0" encoding="UTF-8"?>
<!-- Browser-only stylesheet: RSS readers ignore this and read the raw XML.
     When feed.xml is opened directly in a browser it renders as a basic page. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <title><xsl:value-of select="rss/channel/title"/></title>
        <style>
          :root { color-scheme: light dark; }
          body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                 max-width: 820px; margin: 0 auto; padding: 24px 16px; line-height: 1.5; }
          header { border-bottom: 1px solid #8884; padding-bottom: 12px; margin-bottom: 20px; }
          h1 { margin: 0 0 4px; font-size: 1.5rem; }
          .meta { color: #8a8a8a; font-size: 0.9rem; }
          .note { background: #8881; border-radius: 8px; padding: 10px 14px; font-size: 0.9rem; margin-bottom: 20px; }
          .item { margin-bottom: 22px; }
        </style>
      </head>
      <body>
        <header>
          <h1><xsl:value-of select="rss/channel/title"/></h1>
          <div class="meta"><xsl:value-of select="rss/channel/description"/></div>
          <div class="meta">Updated: <xsl:value-of select="rss/channel/lastBuildDate"/></div>
        </header>
        <div class="note">
          This is an RSS feed. Subscribe in your RSS reader or Zotero with this page's URL.
        </div>
        <xsl:for-each select="rss/channel/item">
          <div class="item">
            <!-- description contains the paper's HTML card; render it as HTML. -->
            <xsl:value-of select="description" disable-output-escaping="yes"/>
          </div>
        </xsl:for-each>
        <xsl:if test="not(rss/channel/item)">
          <p>No new papers today. Take a rest!</p>
        </xsl:if>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>

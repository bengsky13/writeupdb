import Link from "next/link";

type PaginationProps = {
  page: number;
  totalPages: number;
  makeHref: (page: number) => string;
};

export function Pagination({ page, totalPages, makeHref }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const pages = buildPageList(page, totalPages);

  return (
    <nav className="pagination" aria-label="Pagination">
      <Link
        className={`adminNavLink ${page <= 1 ? "isDisabled" : ""}`}
        href={page > 1 ? makeHref(page - 1) : makeHref(1)}
        aria-disabled={page <= 1}
      >
        Previous
      </Link>
      <div className="paginationPages">
        {pages.map((item, index) =>
          item === "ellipsis" ? (
            <span key={`ellipsis-${index}`} className="paginationEllipsis">
              …
            </span>
          ) : (
            <Link
              key={item}
              className={`adminNavLink paginationPageLink ${item === page ? "isCurrentPage" : ""}`}
              href={makeHref(item)}
              aria-current={item === page ? "page" : undefined}
            >
              {item}
            </Link>
          ),
        )}
      </div>
      <Link
        className={`adminNavLink ${page >= totalPages ? "isDisabled" : ""}`}
        href={page < totalPages ? makeHref(page + 1) : makeHref(totalPages)}
        aria-disabled={page >= totalPages}
      >
        Next
      </Link>
    </nav>
  );
}

function buildPageList(page: number, totalPages: number): Array<number | "ellipsis"> {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const start = Math.max(2, page - 1);
  const end = Math.min(totalPages - 1, page + 1);
  const items: Array<number | "ellipsis"> = [1];

  if (start > 2) {
    items.push("ellipsis");
  }

  for (let current = start; current <= end; current += 1) {
    items.push(current);
  }

  if (end < totalPages - 1) {
    items.push("ellipsis");
  }

  items.push(totalPages);
  return items;
}

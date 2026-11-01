using System.Xml.Linq;
using Xunit;

namespace InvoiceApp.Tests;

public class ArchitectureTests
{
    [Fact]
    public void DomainProject_DoesNotReferenceApi()
    {
        var repositoryRoot = FindRepositoryRoot();
        var domainProjectPath = Path.Combine(
            repositoryRoot,
            "backend",
            "src",
            "InvoiceApp.Domain",
            "InvoiceApp.Domain.csproj");

        var project = XDocument.Load(domainProjectPath);
        var apiReferences = project
            .Descendants()
            .Where(element =>
                element.Name.LocalName is "ProjectReference" or "Reference")
            .Select(element => (string?)element.Attribute("Include"))
            .Where(include => include is not null)
            .Where(include =>
            {
                var reference = include!.Split(',')[0].Replace('\\', '/');
                return Path.GetFileNameWithoutExtension(reference) == "InvoiceApp.Api";
            })
            .ToArray();

        Assert.True(
            apiReferences.Length == 0,
            $"Architecture violation: InvoiceApp.Domain must not reference InvoiceApp.Api. " +
            $"Found reference(s): {string.Join(", ", apiReferences)}");
    }

    private static string FindRepositoryRoot()
    {
        for (var directory = new DirectoryInfo(AppContext.BaseDirectory);
             directory is not null;
             directory = directory.Parent)
        {
            if (File.Exists(Path.Combine(directory.FullName, "backend", "InvoiceApp.sln")))
            {
                return directory.FullName;
            }
        }

        throw new DirectoryNotFoundException(
            "Architecture test could not locate the repository root containing backend/InvoiceApp.sln.");
    }
}
